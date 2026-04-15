"""Human resources models."""

from datetime import datetime
from typing import Annotated, List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field, field_validator

from backend.models.base import MemoryNode, _coerce_date_to_datetime


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
    passport_path: Optional[str] = None  # DEPRECATED - use passport_document_path
    visa_path: Optional[str] = None  # DEPRECATED - use visa_document_path

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
    agency_name: Optional[str] = None  # If from external agency
    agency_contact: Optional[str] = None
    is_preferred_vendor: bool = False  # If this external worker is reliable/preferred

    # ===== SUBSTITUTE MANAGEMENT FIELDS =====
    can_be_substitute: bool = False  # Outsourced employees who can fill in as substitutes
    substitute_availability: Optional[str] = None  # "available" | "assigned" | "unavailable"
    substitute_rating: Optional[float] = None  # 0–5 star rating for substitute quality
    substitute_skills: List[str] = []  # Skills/roles this substitute can cover

    # Current substitute assignment (if any)
    current_substitute_assignment: Optional[SubstituteAssignment] = None
    substitute_assignment_history: List[SubstituteAssignment] = []

    # Metrics
    total_substitute_assignments: int = 0
    total_days_as_substitute: int = 0

    @field_validator(
        "date_of_birth",
        "civil_id_expiry",
        "passport_expiry",
        "date_of_joining",
        "contract_end_date",
        "current_assignment_start",
        "current_assignment_end",
        mode="before",
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


class Designation(Document, MemoryNode):
    title: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "designations"


class Attendance(Document, MemoryNode):
    employee_uid: Optional[int] = None
    site_uid: Optional[int] = None
    date: str
    status: str
    shift: Optional[str] = "Morning"
    overtime_hours: Optional[int] = 0

    # ===== REPLACEMENT TRACKING (NEW) =====
    is_replacement: bool = False  # True if external worker covering for someone
    replacing_employee_id: Optional[int] = None  # ID of employee being replaced
    replacing_employee_name: Optional[str] = None

    replaced_by_employee_id: Optional[int] = None  # If THIS employee was replaced (sick leave)
    replaced_by_employee_name: Optional[str] = None

    replacement_reason: Optional[str] = None  # "Sick Leave" | "Vacation" | "Emergency"

    # For external workers
    daily_rate_applied: Optional[float] = None  # Rate for this specific day
    hourly_rate_applied: Optional[float] = None
    payment_status: str = "Pending"  # Pending | Paid

    # Temporary assignment link
    temporary_assignment_id: Optional[int] = None  # Link to TemporaryAssignment if applicable

    # ===== MANAGER-RECORDED ATTENDANCE FIELDS (NEW) =====
    recorded_by_manager_id: Optional[int] = None  # Manager who recorded this attendance
    recorded_by_manager_name: Optional[str] = None
    is_substitute: bool = False  # True if this is a substitute worker
    leave_type: Optional[str] = None  # "Sick Leave" | "Annual Leave" | "Emergency Leave"
    leave_reason: Optional[str] = None
    substitute_requested: bool = False  # Manager requested substitute for absent employee
    substitute_assigned_id: Optional[int] = None  # Substitute assigned to cover
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
