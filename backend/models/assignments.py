"""Assignment domain models."""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field, field_validator

from backend.models.base import _coerce_date_to_datetime


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


class EmployeeAssignment(Document):
    """
    Tracks employee assignments to projects/sites.
    Used for company employees assigned for full contract duration.
    """

    uid: int

    # Employee Information
    employee_id: int  # 🔗 Linked to Employee.uid
    employee_name: str
    employee_type: str  # "Company" | "Outsourced"
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
    assigned_date: datetime  # When assignment was created
    assignment_start: datetime  # When employee starts working (usually contract start)
    assignment_end: Optional[datetime] = None  # When assignment ends (None = open-ended)

    # Status
    status: str = "Active"  # Active | Completed | Reassigned | Terminated

    # Notes
    notes: Optional[str] = None
    termination_reason: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    @field_validator("assigned_date", "assignment_start", "assignment_end", mode="before")
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
    employee_id: int  # 🔗 Linked to Employee.uid (external worker)
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
    replacing_employee_id: Optional[int] = None  # If covering for someone
    replacing_employee_name: Optional[str] = None
    replacement_reason: Optional[str] = None  # "Sick Leave" | "Vacation" | "Emergency" | "Additional Coverage"

    # Period (can be just 1 day!)
    start_date: datetime
    end_date: datetime
    total_days: int = 1

    # Payment
    rate_type: str = "Daily"  # Daily | Hourly
    daily_rate: float = 0.0
    hourly_rate: float = 0.0

    # Status
    status: str = "Active"  # Active | Completed | Cancelled

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_admin_id: Optional[int] = None

    @field_validator("start_date", "end_date", mode="before")
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
