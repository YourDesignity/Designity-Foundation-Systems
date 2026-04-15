from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime, date, time
from beanie import Document, Indexed
from pydantic import Field, BaseModel, field_validator


def _coerce_date_to_datetime(v):
    """Convert datetime.date → datetime.datetime for BSON/MongoDB compatibility.

    pymongo's BSON codec does not natively support bare ``datetime.date``
    objects on all platforms (notably Windows).  This helper is used as a
    ``mode='before'`` field validator in every Document that stores date
    fields so that values are always stored as ``datetime.datetime``.
    """
    if isinstance(v, date) and not isinstance(v, datetime):
        return datetime(v.year, v.month, v.day)
    return v

# =============================================================================
# 1. UTILITIES & BASE MODEL
# =============================================================================

class Counter(Document):
    collection_name: Annotated[str, Indexed(unique=True)] 
    current_uid: int = 0
    class Settings:
        name = "counters"

class MemoryNode(BaseModel):
    uid: Optional[int] = None 
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    specs: Dict[str, Any] = {}
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

# =============================================================================
# 1b. SUBSTITUTE ASSIGNMENT EMBEDDED MODEL
# =============================================================================

class SubstituteAssignment(BaseModel):
    """Represents a temporary substitute assignment for an outsourced employee."""
    site_id: int
    site_name: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    reason: str  # "sick_leave" | "vacation" | "shortage" | "emergency"
    replacing_employee_id: Optional[int] = None
    replacing_employee_name: Optional[str] = None
    assigned_by_manager_id: int
    daily_rate: Optional[float] = None
    hourly_rate: Optional[float] = None
    status: str = "Active"  # Active | Completed | Cancelled

# =============================================================================
# 2. CORE ENTITIES
# =============================================================================

class Admin(Document, MemoryNode):
    email: Annotated[str, Indexed(unique=True)]
    hashed_password: str
    full_name: str
    designation: str
    role: str                       
    permissions: List[str] = []     
    assigned_site_uids: List[int] = []
    has_manager_profile: bool = False
    phone: Optional[str] = None
    profile_photo: Optional[str] = None
    class Settings:
        name = "admins"

class Employee(Document, MemoryNode):
    # ===== BASIC INFO =====
    name: str
    designation: str
    status: str = "Active"

    # ===== EMPLOYEE TYPE =====
    employee_type: str = "Company"  # "Company" | "Outsourced"

    # ===== PERSONAL DETAILS =====
    date_of_birth: Optional[datetime] = None
    nationality: Optional[str] = None
    permanent_address: Optional[str] = None

    # ===== CONTACT INFORMATION =====
    phone_kuwait: Optional[str] = None
    phone_home_country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None

    # ===== IDENTITY DOCUMENTS =====
    civil_id_number: Optional[str] = None
    civil_id_expiry: Optional[datetime] = None
    civil_id_document_path: Optional[str] = None  # PDF file path

    passport_number: Optional[str] = None
    passport_expiry: Optional[datetime] = None
    passport_document_path: Optional[str] = None  # PDF file path

    visa_document_path: Optional[str] = None  # PDF file path

    # ===== EMPLOYEE PHOTO =====
    photo_path: Optional[str] = None  # Image file path

    # ===== CUSTOM LOCAL STORAGE PATHS (user-accessible folder) =====
    custom_photo_path: Optional[str] = None
    custom_civil_id_path: Optional[str] = None
    custom_passport_path: Optional[str] = None
    custom_visa_path: Optional[str] = None

    # ===== FINANCIAL INFO =====
    basic_salary: float = 0.0
    allowance: float = 0.0
    standard_work_days: int = 28
    default_hourly_rate: float = 0.0  # Used for Outsourced employees

    # ===== EMPLOYMENT DETAILS =====
    date_of_joining: Optional[datetime] = None
    contract_end_date: Optional[datetime] = None  # For Outsourced employees

    # ===== DEPRECATED FIELDS (kept for backward compatibility) =====
    passport_path: Optional[str] = None   # DEPRECATED - use passport_document_path
    visa_path: Optional[str] = None       # DEPRECATED - use visa_document_path

    manager_id: Optional[int] = None

    # ===== ASSIGNMENT TRACKING (NEW) =====
    is_currently_assigned: bool = False
    current_assignment_type: Optional[str] = None  # "Permanent" | "Temporary" | None
    current_project_id: Optional[int] = None
    current_project_name: Optional[str] = None
    current_site_id: Optional[int] = None
    current_site_name: Optional[str] = None
    current_manager_id: Optional[int] = None
    current_manager_name: Optional[str] = None
    current_assignment_start: Optional[datetime] = None
    current_assignment_end: Optional[datetime] = None

    # Assignment History (list of assignment UIDs)
    assignment_history_ids: List[int] = []

    # Availability Status
    availability_status: str = "Available"  # Available | Assigned | On Leave | Sick

    # For Outsourced Employees Only
    agency_name: Optional[str] = None      # If from external agency
    agency_contact: Optional[str] = None
    is_preferred_vendor: bool = False      # If this external worker is reliable/preferred

    # ===== SUBSTITUTE MANAGEMENT FIELDS =====
    can_be_substitute: bool = False        # Outsourced employees who can fill in as substitutes
    substitute_availability: Optional[str] = None  # "available" | "assigned" | "unavailable"
    substitute_rating: Optional[float] = None      # 0–5 star rating for substitute quality
    substitute_skills: List[str] = []             # Skills/roles this substitute can cover

    # Current substitute assignment (if any)
    current_substitute_assignment: Optional[SubstituteAssignment] = None
    substitute_assignment_history: List[SubstituteAssignment] = []

    # Metrics
    total_substitute_assignments: int = 0
    total_days_as_substitute: int = 0

    @field_validator(
        'date_of_birth', 'civil_id_expiry', 'passport_expiry',
        'date_of_joining', 'contract_end_date',
        'current_assignment_start', 'current_assignment_end',
        mode='before'
    )
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "employees"
        indexes = [
            "name",
            "employee_type",
            "status",
            "civil_id_number",
            "passport_number",
            "is_currently_assigned",
            "availability_status",
            "can_be_substitute",
            "substitute_availability",
        ]

class Site(Document, MemoryNode):
    name: Annotated[str, Indexed(unique=True)]
    location: str
    manager_uid: Optional[int] = None
    description: Optional[str] = None
    phone: Optional[str] = None

    # ===== PROJECT WORKFLOW FIELDS (NEW) =====
    site_code: Optional[str] = None           # e.g., "SITE-001"
    project_id: Optional[int] = None          # 🔗 Linked to Project.uid
    project_name: Optional[str] = None        # Denormalized for quick access
    contract_id: Optional[int] = None         # 🔗 Linked to Contract.uid
    contract_code: Optional[str] = None       # Denormalized
    assigned_manager_id: Optional[int] = None # 🔗 Linked to Admin.uid (Site Manager)
    assigned_manager_name: Optional[str] = None  # Denormalized
    required_workers: int = 0                 # How many workers needed
    assigned_workers: int = 0                 # How many currently assigned
    assigned_employee_ids: List[int] = []     # List of Employee.uid assigned to this site
    status: str = "Active"                    # Active | Completed | On Hold
    start_date: Optional[datetime] = None         # When site work started
    completion_date: Optional[datetime] = None    # When site work completed

    # ===== HEADCOUNT MANAGEMENT (NEW) =====
    active_substitute_uids: List[int] = []    # Outsourced/substitute employees currently at this site

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

    @field_validator('start_date', 'completion_date', mode='before')
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
            "status",
        ]

    async def update_workforce_count(self):
        """Update assigned workers count based on assigned_employee_ids list."""
        self.assigned_workers = len(self.assigned_employee_ids)
        await self.save()

class Designation(Document, MemoryNode):
    title: Annotated[str, Indexed(unique=True)]
    class Settings:
        name = "designations"

# =============================================================================
# 3. OPERATIONS
# =============================================================================

class Attendance(Document, MemoryNode):
    employee_uid: Optional[int] = None
    site_uid: Optional[int] = None
    date: str       
    status: str
    shift: Optional[str] = "Morning"
    overtime_hours: Optional[int] = 0

    # ===== REPLACEMENT TRACKING (NEW) =====
    is_replacement: bool = False                        # True if external worker covering for someone
    replacing_employee_id: Optional[int] = None        # ID of employee being replaced
    replacing_employee_name: Optional[str] = None

    replaced_by_employee_id: Optional[int] = None      # If THIS employee was replaced (sick leave)
    replaced_by_employee_name: Optional[str] = None

    replacement_reason: Optional[str] = None           # "Sick Leave" | "Vacation" | "Emergency"

    # For external workers
    daily_rate_applied: Optional[float] = None         # Rate for this specific day
    hourly_rate_applied: Optional[float] = None
    payment_status: str = "Pending"                    # Pending | Paid

    # Temporary assignment link
    temporary_assignment_id: Optional[int] = None      # Link to TemporaryAssignment if applicable

    # ===== MANAGER-RECORDED ATTENDANCE FIELDS (NEW) =====
    recorded_by_manager_id: Optional[int] = None       # Manager who recorded this attendance
    recorded_by_manager_name: Optional[str] = None
    is_substitute: bool = False                         # True if this is a substitute worker
    leave_type: Optional[str] = None                   # "Sick Leave" | "Annual Leave" | "Emergency Leave"
    leave_reason: Optional[str] = None
    substitute_requested: bool = False                  # Manager requested substitute for absent employee
    substitute_assigned_id: Optional[int] = None       # Substitute assigned to cover
    notes: Optional[str] = None
    recorded_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "attendance"
        indexes = [
            [("employee_uid", 1), ("date", 1)],
            [("site_uid", 1), ("date", 1)],
            [("recorded_by_manager_id", 1), ("date", 1)],
        ]

class Schedule(Document, MemoryNode):
    employee_uid: Optional[int] = None
    site_uid: int
    work_date: str
    task: str
    shift_type: Optional[str] = None
    class Settings:
        name = "schedules"
        indexes = [[("employee_uid", 1), ("work_date", 1)]]

class Overtime(Document, MemoryNode):
    employee_uid: Optional[int] = None
    date: str
    hours: float
    type: str 
    reason: Optional[str] = None
    class Settings:
        name = "overtime"

class Deduction(Document, MemoryNode):
    employee_uid: Optional[int] = None
    pay_period: str
    amount: float
    reason: Optional[str] = None
    class Settings:
        name = "deductions"

class DutyAssignment(Document):
    """
    Duty assignment join table.

    IMPORTANT: Uses ``*_id`` convention (not ``*_uid``) by design:
    - ``employee_id`` references ``Employee.uid``
    - ``site_id`` references ``Site.uid``
    - ``manager_id`` references ``Admin.uid``

    This is intentional. The frontend handles both patterns defensively
    (``emp.id || emp.uid``). Do NOT change this to ``*_uid`` naming.

    Note: ``manager_id``, ``start_date``, and ``end_date`` are Optional for
    backward compatibility with legacy records created before these fields
    were required. New records always populate all fields.
    """
    employee_id: int
    site_id: int
    manager_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    class Settings:
        name = "duty_assignments"

# =============================================================================
# 4. VEHICLE MANAGEMENT
# =============================================================================

class Vehicle(Document, MemoryNode):
    model: str
    plate: Annotated[str, Indexed(unique=True)]
    type: str  
    status: str = "Available" 
    current_mileage: float = 0.0
    registration_expiry: Optional[str] = None 
    insurance_expiry: Optional[str] = None
    pollution_expiry: Optional[str] = None
    class Settings:
        name = "vehicles"

class TripLog(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    driver_name: str
    out_time: Optional[datetime] = None
    in_time: Optional[datetime] = None
    purpose: str
    status: str = "Ongoing"
    start_mileage: float = 0.0
    end_mileage: float = 0.0 
    start_condition: str = "Good"
    end_condition: Optional[str] = None
    class Settings:
        name = "vehicle_trips"

class VehicleExpense(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    driver_name: str
    category: str
    amount: float
    date: str
    description: Optional[str] = None
    class Settings:
        name = "vehicle_expenses"

class MaintenanceLog(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    service_type: str 
    cost: float
    service_date: str
    next_due_date: Optional[str] = None
    notes: Optional[str] = None
    class Settings:
        name = "vehicle_maintenance"

class FuelLog(Document, MemoryNode):
    vehicle_uid: int
    vehicle_plate: Optional[str] = None
    date: str
    liters: float
    cost: float
    odometer: float
    filled_by: Optional[str] = None
    class Settings:
        name = "vehicle_fuel"

# =============================================================================
# 5. CONTRACTS & INVOICE MANAGEMENT
# =============================================================================

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

class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_rate: float
    total: float

class Invoice(Document, MemoryNode):
    invoice_no: Optional[str] = None # FIXED: Made optional for 422 error
    project_uid: int
    client_name: str
    date: str
    due_date: str
    items: List[InvoiceItem] = []
    total_amount: float
    status: str = "Unpaid"
    class Settings:
        name = "invoices"

# =============================================================================
# 6. INVENTORY MANAGEMENT
# =============================================================================

class InventoryItem(Document, MemoryNode):
    name: str
    category: str 
    stock: int
    unit: str      
    price: float   
    supplier: Optional[str] = None
    status: str = "In Stock"
    class Settings:
        name = "inventory_items"


# =============================================================================
# 6b. MATERIAL MANAGEMENT (Inventory-Based Projects)
# =============================================================================

class Material(Document, MemoryNode):
    """Material master data for inventory-based project costing."""
    material_code: str
    name: str
    category: str = "raw_material"  # "raw_material" | "finished_good" | "consumable" | "tool"
    unit_of_measure: str = "pcs"    # "pcs", "kg", "m", "m2", "m3", "ltr", "roll"
    current_stock: float = 0.0
    minimum_stock: float = 0.0
    unit_cost: float = 0.0
    description: Optional[str] = None

    class Settings:
        name = "materials"
        indexes = ["uid", "material_code", "name", "category"]


class Supplier(Document, MemoryNode):
    """Supplier / vendor master data."""
    supplier_code: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

    class Settings:
        name = "suppliers"
        indexes = ["uid", "supplier_code", "name"]


class PurchaseOrderItem(BaseModel):
    material_id: int
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    quantity: float
    unit_cost: float
    total_cost: float = 0.0


class PurchaseOrder(Document, MemoryNode):
    """Purchase order for procuring materials from a supplier."""
    po_number: str
    supplier_id: int
    supplier_name: Optional[str] = None
    items: List[PurchaseOrderItem] = []
    total_amount: float = 0.0
    status: str = "pending"       # "pending" | "received" | "partial" | "cancelled"
    notes: Optional[str] = None
    ordered_by_admin_id: Optional[int] = None
    expected_delivery: Optional[datetime] = None
    received_at: Optional[datetime] = None

    @field_validator('expected_delivery', 'received_at', mode='before')
    @classmethod
    def coerce_po_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "purchase_orders"
        indexes = ["uid", "po_number", "supplier_id", "status"]


class MaterialMovement(Document, MemoryNode):
    """Tracks stock IN/OUT movements for each material."""
    material_id: int
    material_name: Optional[str] = None
    movement_type: str            # "IN" | "OUT"
    quantity: float
    unit_cost: float = 0.0
    total_cost: float = 0.0
    reference_type: Optional[str] = None   # "purchase_order" | "contract_usage" | "adjustment"
    reference_id: Optional[int] = None     # PO uid or contract uid
    reference_code: Optional[str] = None   # PO number or contract code
    notes: Optional[str] = None
    performed_by_admin_id: Optional[int] = None

    class Settings:
        name = "material_movements"
        indexes = ["uid", "material_id", "movement_type", "reference_id"]


# =============================================================================
# 7. PROJECT WORKFLOW SYSTEM (NEW)
# =============================================================================

class Project(Document):
    """
    Main project entity - represents a client project/contract work.
    """
    uid: int

    # Basic Information
    project_code: str              # e.g., "PRJ-001"
    project_name: str              # e.g., "Al-Mansour Mall Construction"
    client_name: str
    client_contact: Optional[str] = None
    client_email: Optional[str] = None
    description: Optional[str] = None

    # Status
    status: str = "Active"         # Active | Completed | On Hold | Cancelled

    # Relationships (UIDs for linking)
    contract_ids: List[int] = []   # Can have multiple contracts
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
        sites = await Site.find(Site.project_id == self.uid).to_list()
        self.total_sites = len(sites)
        self.site_ids = [s.uid for s in sites if s.uid is not None]

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.project_id == self.uid,
            EmployeeAssignment.status == "Active"
        ).to_list()
        self.total_assigned_employees = len(assignments)

        manager_ids = {s.assigned_manager_id for s in sites if s.assigned_manager_id}
        self.total_assigned_managers = len(manager_ids)

        self.updated_at = datetime.now()
        await self.save()


class Contract(Document):
    """
    Contract entity - linked to a project, defines work period and terms.
    """
    uid: int

    # Basic Information
    contract_code: str             # e.g., "CNT-001"
    contract_name: Optional[str] = None

    # Project Linking
    project_id: int                # 🔗 Linked to Project.uid
    project_name: Optional[str] = None  # Denormalized for quick access

    # Contract Period
    start_date: datetime
    end_date: datetime

    # Financial
    contract_value: float = 0.0    # Total contract value in KD
    payment_terms: Optional[str] = None  # e.g., "Monthly", "Milestone-based"

    # Terms & Conditions
    contract_terms: Optional[str] = None
    notes: Optional[str] = None

    # Status
    status: str = "Active"         # Active | Expired | Terminated | Completed

    # Relationships
    site_ids: List[int] = []

    # Auto-calculated fields
    duration_days: int = 0         # Calculated from start_date and end_date
    days_remaining: int = 0        # Days until expiry
    is_expiring_soon: bool = False  # True if < 30 days remaining

    # Document attachment
    document_path: Optional[str] = None   # Uploaded contract PDF file path
    document_name: Optional[str] = None   # Original filename

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
        ]

    @field_validator('start_date', 'end_date', mode='before')
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


class EmployeeAssignment(Document):
    """
    Tracks employee assignments to projects/sites.
    Used for company employees assigned for full contract duration.
    """
    uid: int

    # Employee Information
    employee_id: int               # 🔗 Linked to Employee.uid
    employee_name: str
    employee_type: str             # "Company" | "Outsourced"
    employee_designation: Optional[str] = None

    # Assignment Details
    assignment_type: str = "Permanent"  # Permanent | Temporary

    # Project/Site Linking
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    contract_id: Optional[int] = None
    site_id: int
    site_name: str
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None

    # Assignment Period
    assigned_date: datetime            # When assignment was created
    assignment_start: datetime         # When employee starts working (usually contract start)
    assignment_end: Optional[datetime] = None  # When assignment ends (None = open-ended)

    # Status
    status: str = "Active"         # Active | Completed | Reassigned | Terminated

    # Notes
    notes: Optional[str] = None
    termination_reason: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    @field_validator('assigned_date', 'assignment_start', 'assignment_end', mode='before')
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "employee_assignments"
        indexes = [
            "uid",
            "employee_id",
            "project_id",
            "site_id",
            "manager_id",
            "status",
            "assignment_start",
            "assignment_end",
        ]


class TemporaryAssignment(Document):
    """
    Tracks temporary worker assignments (external/outsourced workers).
    Used when company employees are on sick leave or additional workers are needed.
    """
    uid: int

    # Worker Information
    employee_id: int               # 🔗 Linked to Employee.uid (external worker)
    employee_name: str
    employee_type: str = "Outsourced"
    employee_designation: Optional[str] = None

    # Assignment Details
    assignment_type: str = "Temporary"

    # Site Linking
    site_id: int
    site_name: str
    project_id: int
    manager_id: int

    # Replacement Details
    replacing_employee_id: Optional[int] = None    # If covering for someone
    replacing_employee_name: Optional[str] = None
    replacement_reason: Optional[str] = None       # "Sick Leave" | "Vacation" | "Emergency" | "Additional Coverage"

    # Period (can be just 1 day!)
    start_date: datetime
    end_date: datetime
    total_days: int = 1

    # Payment
    rate_type: str = "Daily"       # Daily | Hourly
    daily_rate: float = 0.0
    hourly_rate: float = 0.0

    # Status
    status: str = "Active"         # Active | Completed | Cancelled

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "temporary_assignments"
        indexes = [
            "uid",
            "employee_id",
            "site_id",
            "replacing_employee_id",
            "start_date",
            "end_date",
            "status",
        ]


# =============================================================================
# 8. MESSAGING SYSTEM
# =============================================================================

class Conversation(Document, MemoryNode):
    """
    Represents a message thread (broadcast or private chat).

    Types:
    - broadcast_all: Everyone can see
    - broadcast_managers: Only managers + admins (Phase 2)
    - broadcast_employees: Only employees + admins (Phase 2)
    - broadcast_custom: Selected recipients only (Phase 2)
    - private: One-on-one chat (Phase 3)
    """
    conversation_type: str  # "broadcast_all", "broadcast_managers", "broadcast_employees", "broadcast_custom", "private"
    created_by_id: int  # Admin.uid who created conversation
    created_by_name: str  # For display purposes
    created_by_role: str  # "SuperAdmin", "Admin", "Site Manager", "Employee"

    participant_ids: List[int] = []  # UIDs of people who can see this thread
    participant_names: List[str] = []  # For display (denormalized for performance)

    title: str  # "Broadcast: All", "Chat with Manager John", etc.
    last_message_at: datetime = Field(default_factory=datetime.now)
    last_message_preview: Optional[str] = None  # First 50 chars of last message

    unread_count_map: Dict[str, int] = {}  # {str(user_id): unread_count}

    class Settings:
        name = "conversations"
        indexes = [
            [("created_by_id", 1)],
            [("last_message_at", -1)]
        ]


class Message(Document, MemoryNode):
    """
    Individual message within a conversation thread.
    """
    conversation_id: int  # Links to Conversation.uid

    sender_id: int  # Who sent it (Admin.uid / Employee.uid)
    sender_name: str  # Display name
    sender_role: str  # "SuperAdmin", "Admin", "Site Manager", "Employee"
    sender_type: str  # "admin", "manager", "employee" (lowercase for filtering)

    content: str  # Message text
    timestamp: datetime = Field(default_factory=datetime.now)

    read_by_ids: List[int] = []  # UIDs of users who have read this message

    class Settings:
        name = "messages"
        indexes = [
            [("conversation_id", 1), ("timestamp", -1)],
            [("sender_id", 1)]
        ]

# =============================================================================
# 8. MANAGER PROFILE
# =============================================================================

class ManagerProfile(Document):
    """
    Manager Profile - Stores detailed information about Site Managers.
    Linked to Admin table via admin_id.
    """
    uid: int
    admin_id: int  # Foreign key to Admin.uid

    # Required Fields
    full_name: str
    designation: str
    monthly_salary: float
    allowances: float = 0.0
    date_of_joining: datetime
    is_active: bool = True

    # Optional Fields
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    civil_id: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: int

    class Settings:
        name = "manager_profiles"
        indexes = [
            "admin_id",
            "full_name",
            "is_active"
        ]




















# =============================================================================
# 8. MANAGER ATTENDANCE SYSTEM
# =============================================================================

class ManagerAttendanceConfig(Document):
    """
    Manager Attendance Configuration - Customizable check-in windows per manager.
    Each manager can have different time windows set by admin.
    """
    uid: int
    manager_id: int  # Foreign key to Admin.uid (Site Manager)

    # Morning Segment
    morning_enabled: bool = True
    morning_window_start: str = "08:00"  # HH:MM (24-hour)
    morning_window_end: str = "09:30"    # HH:MM (24-hour)

    # Afternoon Segment
    afternoon_enabled: bool = True
    afternoon_window_start: str = "13:00"  # HH:MM (24-hour)
    afternoon_window_end: str = "14:00"    # HH:MM (24-hour)

    # Evening Segment
    evening_enabled: bool = True
    evening_window_start: str = "17:00"  # HH:MM (24-hour)
    evening_window_end: str = "18:30"    # HH:MM (24-hour)

    # Rules
    require_all_segments: bool = True

    # Metadata
    configured_by_admin_id: int
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "manager_attendance_configs"
        indexes = ["manager_id"]


class ManagerAttendance(Document):
    """
    Manager Attendance Record - Tracks daily 3-segment check-ins.
    """
    uid: int
    manager_id: int  # Foreign key to Admin.uid (Site Manager)
    date: date

    # Morning Segment
    morning_check_in: Optional[datetime] = None
    morning_status: Optional[str] = None  # "On Time" | "Late" | "Missed" | "Admin Override" | "Disabled"

    # Afternoon Segment
    afternoon_check_in: Optional[datetime] = None
    afternoon_status: Optional[str] = None

    # Evening Segment
    evening_check_out: Optional[datetime] = None
    evening_status: Optional[str] = None

    # Overall Day Status
    day_status: str = "Pending"  # "Full Day" | "Partial" | "Absent" | "Leave" | "Pending"

    # Override Information
    is_overridden: bool = False
    overridden_by_admin_id: Optional[int] = None
    override_reason: Optional[str] = None
    override_timestamp: Optional[datetime] = None

    # Additional Info
    notes: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "manager_attendance"
        indexes = [
            "manager_id",
            "date",
            [("manager_id", 1), ("date", -1)]
        ]



# =============================================================================
# 9. COMPANY SETTINGS
# =============================================================================

class CompanySettings(Document):
    """
    Company-wide configuration for salary calculations and business rules.
    Only one settings document should exist (singleton pattern).
    """
    uid: int = 1  # Always 1 (singleton)

    # Overtime Multipliers
    normal_overtime_multiplier: float = 1.25      # Normal OT rate (default: 25% premium)
    offday_overtime_multiplier: float = 1.5       # Off-day OT rate (default: 50% premium)

    # Work Hours
    standard_hours_per_day: int = 8               # Default work hours per day

    # Absence Penalties
    enable_absence_deduction: bool = True         # Whether to deduct for absences

    # File Storage Configuration
    custom_storage_path: Optional[str] = None     # e.g., "D:\\MONTREAL_Files"
    enable_local_storage: bool = True             # Enable/disable custom folder backup
    use_employee_name_in_filename: bool = True    # Use "13_Naveen.jpg" vs "emp_13_20260404.jpg"

    # Metadata
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_admin_id: Optional[int] = None
    updated_by_admin_name: Optional[str] = None

    # ===== PROJECT WORKFLOW SETTINGS (NEW) =====
    auto_generate_project_codes: bool = True   # Auto-generate PRJ-001, PRJ-002, etc.
    auto_generate_contract_codes: bool = True  # Auto-generate CNT-001, CNT-002, etc.
    auto_generate_site_codes: bool = True      # Auto-generate SITE-001, SITE-002, etc.

    project_code_prefix: str = "PRJ"
    contract_code_prefix: str = "CNT"
    site_code_prefix: str = "SITE"

    # Contract expiry alerts
    contract_expiry_warning_days: int = 30     # Alert when contract expires in X days

    # External worker settings
    default_external_worker_daily_rate: float = 15.0    # Default daily rate in KD
    default_external_worker_hourly_rate: float = 1.875  # Default hourly rate in KD

    class Settings:
        name = "company_settings"


