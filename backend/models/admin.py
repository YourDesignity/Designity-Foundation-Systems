"""Admin and manager domain models."""

from datetime import date, datetime
from typing import Annotated, List, Optional

from beanie import Document, Indexed
from pydantic import Field, field_validator

from backend.models.base import MemoryNode, _coerce_date_to_datetime


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
            "is_active",
        ]


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
    morning_window_end: str = "09:30"  # HH:MM (24-hour)

    # Afternoon Segment
    afternoon_enabled: bool = True
    afternoon_window_start: str = "13:00"  # HH:MM (24-hour)
    afternoon_window_end: str = "14:00"  # HH:MM (24-hour)

    # Evening Segment
    evening_enabled: bool = True
    evening_window_start: str = "17:00"  # HH:MM (24-hour)
    evening_window_end: str = "18:30"  # HH:MM (24-hour)

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

    @field_validator("date", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "manager_attendance"
        indexes = [
            "manager_id",
            "date",
            [("manager_id", 1), ("date", -1)],
        ]
