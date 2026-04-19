"""Base contract abstract model for polymorphic contract types (Phase 5A)."""

from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import Field, field_validator

from backend.models.base import _coerce_date_to_datetime
from backend.models.role_contracts import ContractRoleSlot


class BaseContract(Document):
    """
    Polymorphic base for all contract types.

    Defines the interface that ALL contracts must implement.
    Stores to the ``contracts`` collection; Beanie inserts a ``_type``
    discriminator so each concrete sub-class can be stored and queried
    independently.

    Backward-compatible superset of the legacy ``Contract`` document:
    every field from the original model is preserved so that existing
    service code and serialised MongoDB documents continue to work
    unchanged.
    """

    # ── Core identification ─────────────────────────────────────────────────
    uid: int
    contract_code: str
    contract_name: Optional[str] = None

    # ── Contract type tag (kept for legacy; new code uses sub-class) ────────
    contract_type: str = "Labour"

    # ── Project / client linkage ────────────────────────────────────────────
    project_id: int
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
    status: str = "Active"  # Active | Expired | Terminated | Completed | On Hold | Cancelled

    # ── Relationships ───────────────────────────────────────────────────────
    site_ids: List[int] = []

    # ── Auto-calculated ─────────────────────────────────────────────────────
    duration_days: int = 0
    days_remaining: int = 0
    is_expiring_soon: bool = False

    # ── Document attachment ──────────────────────────────────────────────────
    document_path: Optional[str] = None
    document_name: Optional[str] = None

    # ── Role-based labour fields (legacy Phase 1) ────────────────────────────
    role_slots: List[ContractRoleSlot] = []
    total_daily_cost: float = 0.0
    total_role_slots: int = 0
    roles_by_designation: Dict[str, int] = {}

    # ── Module / strategy configuration (Phase 5A / 5C) ────────────────────
    enabled_modules: List[str] = []      # e.g. ["employee", "inventory"]
    module_config: Dict[str, Any] = {}   # Per-module settings (Phase 5C)
    salary_strategy: str = "fixed"       # "fixed" | "role_based" | "mixed" | "none"
    cost_strategy: str = "standard"
    invoice_strategy: str = "milestone"
    workflow_config: Dict[str, Any] = {}

    # ── Workflow state (Phase 5D) ────────────────────────────────────────────
    workflow_state: str = "DRAFT"        # DRAFT | PENDING_APPROVAL | ACTIVE | SUSPENDED | COMPLETED | CANCELLED
    workflow_metadata: Dict[str, Any] = {}
    state_changed_at: Optional[datetime] = None
    state_changed_by: Optional[int] = None

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    class Settings:
        is_root = True          # Enables Beanie polymorphism
        name = "contracts"      # Shared MongoDB collection
        indexes = [
            "uid",
            "contract_code",
            "project_id",
            "status",
            "end_date",
            "contract_type",
        ]

    # ── Validators ───────────────────────────────────────────────────────────

    @field_validator("contract_type", mode="before")
    @classmethod
    def validate_contract_type(cls, v: str) -> str:
        # "Equipment Rental" retained for backward compat with existing data;
        # EquipmentRentalContract will be added in a future phase.
        allowed = {"Labour", "Goods Supply", "Equipment Rental", "Role-Based", "Hybrid"}
        if v not in allowed:
            raise ValueError(
                f"contract_type must be one of {sorted(allowed)}, got '{v}'"
            )
        return v

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    # ── Legacy helper methods (carried over from original Contract) ───────────

    async def calculate_duration(self) -> None:
        """Calculate contract duration and days remaining, then save."""
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
        """Recalculate role slot summary fields from current role_slots list."""
        self.total_role_slots = len(self.role_slots)
        self.total_daily_cost = sum(s.daily_rate for s in self.role_slots)
        counts: Dict[str, int] = {}
        for slot in self.role_slots:
            counts[slot.designation] = counts.get(slot.designation, 0) + 1
        self.roles_by_designation = counts

    # ── Phase 5A interface – override in concrete sub-classes ────────────────

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        """Calculate total cost for this contract for a given month."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement calculate_monthly_cost()"
        )

    async def calculate_employee_salary(
        self, employee_id: int, month: int, year: int
    ) -> float:
        """Calculate salary for an employee for a given month."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement calculate_employee_salary()"
        )

    async def get_required_resources(self) -> Dict[str, Any]:
        """Get resources needed for this contract (employees, inventory, vehicles)."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement get_required_resources()"
        )

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        """Check if contract requirements are being met."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement validate_fulfillment()"
        )
