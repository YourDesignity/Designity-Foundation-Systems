"""Base contract abstract model — all contract types extend this."""

from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import Field, field_validator

from backend.models.base import _coerce_date_to_datetime
from backend.models.role_contracts import ContractRoleSlot


# ---------------------------------------------------------------------------
# Contract type constants — single source of truth for the entire backend
# ---------------------------------------------------------------------------

class ContractType:
    DEDICATED_STAFF = "DEDICATED_STAFF"   # Was: Labour — fixed named employees
    SHIFT_BASED     = "SHIFT_BASED"       # Was: Role-Based — daily slot filling
    GOODS_STORAGE   = "GOODS_STORAGE"     # Was: Goods Supply — collect & store
    TRANSPORTATION  = "TRANSPORTATION"    # Was: Equipment Rental — vehicles + drivers
    HYBRID          = "HYBRID"            # Was: Hybrid — combination

    ALL = {
        DEDICATED_STAFF,
        SHIFT_BASED,
        GOODS_STORAGE,
        TRANSPORTATION,
        HYBRID,
    }

    # Backward-compat map — old DB values → new values
    LEGACY_MAP = {
        "Labour":           DEDICATED_STAFF,
        "Role-Based":       SHIFT_BASED,
        "Goods Supply":     GOODS_STORAGE,
        "Equipment Rental": TRANSPORTATION,
        "Hybrid":           HYBRID,
    }

    # Human-readable display labels (used in API responses + frontend)
    LABELS = {
        DEDICATED_STAFF: "Dedicated Staff",
        SHIFT_BASED:     "Shift-Based",
        GOODS_STORAGE:   "Goods & Storage",
        TRANSPORTATION:  "Transportation",
        HYBRID:          "Hybrid",
    }

    @classmethod
    def display(cls, value: str) -> str:
        return cls.LABELS.get(value, value)


class BaseContract(Document):
    """
    Polymorphic base for all contract types.
    Stores to the 'contracts' collection; Beanie inserts a _type
    discriminator so each sub-class can be queried independently.
    All legacy fields preserved for backward compatibility.
    """

    # ── Core identification ─────────────────────────────────────────────────
    uid: int
    contract_code: str
    contract_name: Optional[str] = None

    # ── Contract type ───────────────────────────────────────────────────────
    contract_type: str = ContractType.DEDICATED_STAFF

    # ── Project / client linkage ────────────────────────────────────────────
    project_id: int                        # REQUIRED — cannot exist without project
    project_name: Optional[str] = None
    client_name: Optional[str] = None

    # ── Period ──────────────────────────────────────────────────────────────
    start_date: datetime
    end_date: datetime

    # ── Financials ──────────────────────────────────────────────────────────
    contract_value: float = 0.0
    payment_terms: Optional[str] = None

    # ── Terms ───────────────────────────────────────────────────────────────
    contract_terms: Optional[str] = None
    notes: Optional[str] = None

    # ── Status ──────────────────────────────────────────────────────────────
    status: str = "Active"

    # ── Relationships ───────────────────────────────────────────────────────
    site_ids: List[int] = []

    # ── Auto-calculated ─────────────────────────────────────────────────────
    duration_days: int = 0
    days_remaining: int = 0
    is_expiring_soon: bool = False

    # ── Document attachment ──────────────────────────────────────────────────
    document_path: Optional[str] = None
    document_name: Optional[str] = None

    # ── Role/shift fields (used by DEDICATED_STAFF + SHIFT_BASED) ───────────
    role_slots: List[ContractRoleSlot] = []
    total_daily_cost: float = 0.0
    total_role_slots: int = 0
    roles_by_designation: Dict[str, int] = {}

    # ── Module / strategy config ─────────────────────────────────────────────
    enabled_modules: List[str] = []
    module_config: Dict[str, Any] = {}
    salary_strategy: str = "fixed"
    cost_strategy: str = "standard"
    invoice_strategy: str = "milestone"
    workflow_config: Dict[str, Any] = {}

    # ── Workflow state ───────────────────────────────────────────────────────
    workflow_state: str = "DRAFT"
    workflow_metadata: Dict[str, Any] = {}
    state_changed_at: Optional[datetime] = None
    state_changed_by: Optional[int] = None

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    class Settings:
        is_root = True
        name = "contracts"
        indexes = [
            "uid", "contract_code", "project_id",
            "status", "end_date", "contract_type",
        ]

    @field_validator("contract_type", mode="before")
    @classmethod
    def validate_and_migrate_contract_type(cls, v: str) -> str:
        """Accept new values AND silently migrate legacy values from old DB records."""
        # Migrate legacy value if present
        if v in ContractType.LEGACY_MAP:
            return ContractType.LEGACY_MAP[v]
        if v not in ContractType.ALL:
            raise ValueError(
                f"contract_type must be one of {sorted(ContractType.ALL)}, got '{v}'"
            )
        return v

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    async def calculate_duration(self) -> None:
        if self.start_date and self.end_date:
            self.duration_days = (self.end_date - self.start_date).days
            today = datetime.combine(date.today(), time.min)
            if today < self.end_date:
                self.days_remaining = (self.end_date - today).days
                self.is_expiring_soon = self.days_remaining <= 30
            else:
                self.days_remaining = 0
                self.is_expiring_soon = False
                if self.status == "Active":
                    self.status = "Expired"
        self.updated_at = datetime.now()
        await self.save()

    def recalculate_role_summary(self) -> None:
        self.total_role_slots = len(self.role_slots)
        self.total_daily_cost = sum(s.daily_rate for s in self.role_slots)
        counts: Dict[str, int] = {}
        for slot in self.role_slots:
            counts[slot.designation] = counts.get(slot.designation, 0) + 1
        self.roles_by_designation = counts

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        raise NotImplementedError(f"{type(self).__name__} must implement calculate_monthly_cost()")

    async def calculate_employee_salary(self, employee_id: int, month: int, year: int) -> float:
        raise NotImplementedError(f"{type(self).__name__} must implement calculate_employee_salary()")

    async def get_required_resources(self) -> Dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} must implement get_required_resources()")

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} must implement validate_fulfillment()")
