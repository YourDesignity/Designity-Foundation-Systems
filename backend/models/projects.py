"""Project, site, and contract domain models."""

from datetime import date, datetime, time
from typing import Annotated, Any, Dict, List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field, field_validator

from backend.models.base import MemoryNode, _coerce_date_to_datetime
from backend.models.role_contracts import ContractRoleSlot


class Site(Document, MemoryNode):
    name: Annotated[str, Indexed(unique=True)]
    location: str
    manager_uid: Optional[int] = None
    description: Optional[str] = None
    phone: Optional[str] = None

    # ===== PROJECT WORKFLOW FIELDS (NEW) =====
    site_code: Optional[str] = None  # e.g., "SITE-001"
    project_id: Optional[int] = None  # 🔗 Linked to Project.uid
    project_name: Optional[str] = None  # Denormalized for quick access
    contract_id: Optional[int] = None  # 🔗 Linked to Contract.uid
    contract_code: Optional[str] = None  # Denormalized
    # Multi-manager support: primary single-manager fields kept for backward compat
    assigned_manager_id: Optional[int] = None  # 🔗 Primary manager (legacy / first in list)
    assigned_manager_name: Optional[str] = None  # Denormalized primary manager name
    # New multi-manager list fields
    assigned_manager_ids: List[int] = []  # All managers assigned to this site
    assigned_manager_names: List[str] = []  # Denormalized names for all managers
    required_workers: int = 0  # How many workers needed
    assigned_workers: int = 0  # How many currently assigned
    assigned_employee_ids: List[int] = []  # List of Employee.uid assigned to this site
    status: str = "Active"  # Active | Completed | On Hold
    start_date: Optional[datetime] = None  # When site work started
    completion_date: Optional[datetime] = None  # When site work completed

    # ===== HEADCOUNT MANAGEMENT (NEW) =====
    active_substitute_uids: List[int] = []  # Outsourced/substitute employees currently at this site

    @property
    def current_headcount(self) -> int:
        """Total employees including substitutes."""
        return len(self.assigned_employee_ids) + len(self.active_substitute_uids)

    @property
    def is_understaffed(self) -> bool:
        """True if site has fewer workers than required."""
        return self.required_workers > 0 and self.current_headcount < self.required_workers

    @property
    def headcount_shortage(self) -> int:
        """How many employees the site is short."""
        return max(0, self.required_workers - self.current_headcount)

    @field_validator("start_date", "completion_date", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "sites"
        indexes = [
            "uid",
            "site_code",
            "project_id",
            "contract_id",
            "assigned_manager_id",
            "assigned_manager_ids",
            "status",
        ]

    async def update_workforce_count(self):
        """Update assigned workers count based on assigned_employee_ids list."""
        self.assigned_workers = len(self.assigned_employee_ids)
        await self.save()


class ProjectExpense(BaseModel):
    uid: Optional[int] = None
    category: str
    description: str
    amount: float
    date: datetime = Field(default_factory=datetime.now)


class ContractItem(BaseModel):
    item_code: Optional[str] = None
    description: str
    quantity: float = 0.0
    unit_rate: float = 0.0
    total_value: float = 0.0


class ContractWorkforce(BaseModel):
    name: str
    role: str
    days: int = 0


class ContractSpec(Document, MemoryNode):
    title: str
    client: str
    contract_type: str = "Labour"
    status: str = "Active"
    total_value: float = 0.0
    payment_terms: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    workforce: List[ContractWorkforce] = []
    items: List[ContractItem] = []
    expenses: List[ProjectExpense] = []

    class Settings:
        name = "contract_specs"


class Project(Document):
    """
    Main project entity - represents a client project/contract work.
    """

    uid: int

    # Basic Information
    project_code: str  # e.g., "PRJ-001"
    project_name: str  # e.g., "Al-Mansour Mall Construction"
    client_name: str
    client_contact: Optional[str] = None
    client_email: Optional[str] = None
    description: Optional[str] = None

    # Status
    status: str = "Active"  # Active | Completed | On Hold | Cancelled

    # Relationships (UIDs for linking)
    contract_ids: List[int] = []  # Can have multiple contracts
    site_ids: List[int] = []

    # Metrics (auto-calculated)
    total_sites: int = 0
    total_assigned_employees: int = 0
    total_assigned_managers: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    class Settings:
        name = "projects"
        indexes = [
            "uid",
            "project_code",
            "status",
            "client_name",
        ]

    async def update_metrics(self):
        """Update project metrics (sites count, employees count, etc.)."""
        from backend.models.assignments import EmployeeAssignment

        sites = await Site.find(Site.project_id == self.uid).to_list()
        self.total_sites = len(sites)
        self.site_ids = [s.uid for s in sites if s.uid is not None]

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.project_id == self.uid,
            EmployeeAssignment.status == "Active",
        ).to_list()
        self.total_assigned_employees = len(assignments)

        manager_ids: set[int] = set()
        for s in sites:
            if s.assigned_manager_ids:
                manager_ids.update(s.assigned_manager_ids)
            elif s.assigned_manager_id:
                manager_ids.add(s.assigned_manager_id)
        self.total_assigned_managers = len(manager_ids)

        self.updated_at = datetime.now()
        await self.save()


class Contract(Document):
    """
    Contract entity - linked to a project, defines work period and terms.
    """

    uid: int

    # Basic Information
    contract_code: str  # e.g., "CNT-001"
    contract_name: Optional[str] = None

    # Contract Type (Phase 1)
    contract_type: str = "Labour"  # "Labour" | "Goods Supply" | "Equipment Rental"

    # Project Linking
    project_id: int  # 🔗 Linked to Project.uid
    project_name: Optional[str] = None  # Denormalized for quick access

    # Contract Period
    start_date: datetime
    end_date: datetime

    # Financial
    contract_value: float = 0.0  # Total contract value in KD
    payment_terms: Optional[str] = None  # e.g., "Monthly", "Milestone-based"

    # Terms & Conditions
    contract_terms: Optional[str] = None
    notes: Optional[str] = None

    # Status
    status: str = "Active"  # Active | Expired | Terminated | Completed

    # Relationships
    site_ids: List[int] = []

    # Auto-calculated fields
    duration_days: int = 0  # Calculated from start_date and end_date
    days_remaining: int = 0  # Days until expiry
    is_expiring_soon: bool = False  # True if < 30 days remaining

    # Document attachment
    document_path: Optional[str] = None  # Uploaded contract PDF file path
    document_name: Optional[str] = None  # Original filename

    # ===== ROLE-BASED LABOUR FIELDS (Phase 1) =====
    role_slots: List[ContractRoleSlot] = []  # Fixed role slots for Labour contracts
    total_daily_cost: float = 0.0  # Sum of all slot daily rates
    total_role_slots: int = 0  # Total number of role slots
    roles_by_designation: Dict[str, int] = {}  # e.g. {"Driver": 5, "Cleaner": 10}

    # ===== MODULE CONFIGURATION (Phase 5C) =====
    enabled_modules: List[str] = []  # e.g. ["employee", "inventory", "vehicle"]
    module_config: Dict[str, Any] = {}  # Module-specific settings keyed by module name

    # ===== WORKFLOW FIELDS (Phase 5D) =====
    workflow_state: str = "DRAFT"
    workflow_metadata: Dict[str, Any] = {}
    state_changed_at: Optional[datetime] = None
    state_changed_by: Optional[int] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    class Settings:
        name = "contracts"
        indexes = [
            "uid",
            "contract_code",
            "project_id",
            "status",
            "end_date",
            "contract_type",
        ]

    @field_validator("contract_type", mode="before")
    @classmethod
    def validate_contract_type(cls, v):
        allowed = {"Labour", "Goods Supply", "Equipment Rental"}
        if v not in allowed:
            raise ValueError(f"contract_type must be one of {sorted(allowed)}, got '{v}'")
        return v

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    async def calculate_duration(self):
        """Calculate contract duration and days remaining."""
        if self.start_date and self.end_date:
            self.duration_days = (self.end_date - self.start_date).days

            # Compare at midnight for date-only semantics
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
