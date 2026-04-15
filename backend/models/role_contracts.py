"""Role-based labour contract models."""

from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field, field_validator

from backend.models.base import _coerce_date_to_datetime


class ContractRoleSlot(BaseModel):
    """
    Defines a fixed role slot within a Labour contract.
    e.g., "driver_1" → Driver at 25.0 KWD/day.
    Multiple slots of the same designation are supported.
    """

    slot_id: str  # Unique within contract, e.g. "driver_1"
    designation: str  # Role name, e.g. "Driver", "Cleaner"
    daily_rate: float  # Payment per day in KWD

    # Current assignment (can change day to day via DailyRoleFulfillment)
    current_employee_id: Optional[int] = None
    current_employee_name: Optional[str] = None
    assigned_since: Optional[datetime] = None


class RoleFulfillmentRecord(BaseModel):
    """
    Records which employee filled a specific role slot on a particular day.
    Embedded inside DailyRoleFulfillment.
    """

    slot_id: str
    designation: str
    daily_rate: float

    # Primary employee for the slot
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    is_filled: bool = False

    # Attendance
    attendance_status: str = "Absent"  # "Present" | "Absent" | "Leave" | "Late"

    # Replacement/swap details
    replacement_employee_id: Optional[int] = None
    replacement_employee_name: Optional[str] = None
    replacement_reason: Optional[str] = None

    # Financials
    cost_applied: float = 0.0
    payment_status: str = "Pending"  # "Pending" | "Paid"

    notes: Optional[str] = None


class DailyRoleFulfillment(Document):
    """
    Records which employees filled which role slots on a specific work day.
    One document per (contract_id, date) pair.
    """

    uid: int

    contract_id: int  # 🔗 Linked to Contract.uid
    site_id: int  # 🔗 Linked to Site.uid
    date: datetime  # The work day (stored as midnight datetime)

    role_fulfillments: List[RoleFulfillmentRecord] = []

    # Summary counts
    total_roles_required: int = 0
    total_roles_filled: int = 0
    total_daily_cost: float = 0.0

    # Shortage tracking
    unfilled_slots: List[str] = []  # slot_ids that were not filled
    shortage_cost_impact: float = 0.0  # Revenue/cost lost due to unfilled slots

    # Audit
    recorded_by_manager_id: int
    recorded_at: datetime = Field(default_factory=datetime.now)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("date", "recorded_at", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        return _coerce_date_to_datetime(v)

    class Settings:
        name = "daily_role_fulfillments"
        indexes = [
            "uid",
            [("contract_id", 1), ("date", -1)],
            [("site_id", 1), ("date", -1)],
            "recorded_by_manager_id",
        ]
