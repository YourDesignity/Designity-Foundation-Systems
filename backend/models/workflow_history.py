"""Beanie documents for the Phase 5D workflow audit trail."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import Field


class WorkflowHistory(Document):
    """
    Immutable record of every contract state transition.

    One document is written each time :meth:`WorkflowEngine.transition`
    succeeds.
    """

    contract_id: Optional[int] = None
    from_state: str
    to_state: str
    changed_by: Optional[int] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "workflow_history"
        indexes = [
            "contract_id",
            "from_state",
            "to_state",
            "changed_by",
            "timestamp",
        ]


class ApprovalRequest(Document):
    """
    Tracks a pending or resolved approval workflow for a contract.

    Approval requests are created by :meth:`ApprovalSystem.create_approval_request`
    and resolved via :meth:`ApprovalSystem.approve` / :meth:`ApprovalSystem.reject`.
    """

    contract_id: Optional[int] = None
    approval_type: str
    status: str = "PENDING"
    required_approvers: List[int] = []
    pending_approvers: List[int] = []
    approved_by: List[int] = []
    requested_by: Optional[int] = None
    rejection_reason: Optional[str] = None
    rejected_by: Optional[int] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "approval_requests"
        indexes = [
            "contract_id",
            "approval_type",
            "status",
            "requested_by",
            "created_at",
        ]


class WorkflowEvent(Document):
    """
    Append-only event log used for auditing and debugging.

    One document is written for every event dispatched via
    :class:`EventDispatcher`.
    """

    event_type: str
    payload: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "workflow_events"
        indexes = [
            "event_type",
            "timestamp",
        ]
