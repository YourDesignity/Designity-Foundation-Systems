"""Audit log model for tracking all admin/manager actions."""

from datetime import datetime
from typing import Any, Dict, Optional

from beanie import Document
from pydantic import Field


class AuditLog(Document):
    """
    Immutable record of every significant action performed by admins or managers.

    Lifecycle: written once, never updated (immutable audit trail).
    """

    # Who performed the action
    user_id: int
    user_name: str
    user_role: str

    # What action was performed
    action: str  # e.g. "employee_created", "contract_updated", "attendance_marked"
    category: str  # e.g. "employees", "contracts", "attendance", "payroll", "settings"

    # What entity was affected
    entity_type: str  # e.g. "employee", "contract", "attendance"
    entity_id: Optional[str] = None  # UID or identifier of the affected entity
    entity_name: Optional[str] = None  # Human-readable name

    # Before/after snapshots for updates
    before_data: Optional[Dict[str, Any]] = None
    after_data: Optional[Dict[str, Any]] = None

    # Request context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Description
    description: str = ""

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "audit_logs"
        indexes = [
            "user_id",
            "action",
            "category",
            "entity_type",
            "entity_id",
            "timestamp",
        ]
