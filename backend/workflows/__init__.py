"""
Contract workflow engine — Phase 5D.

Exports:
    WorkflowEngine   — orchestrates contract lifecycle transitions
    ContractState    — enum of all contract states
    ApprovalSystem   — multi-level approval management
    EventDispatcher  — event bus with handler registration
"""

from backend.workflows.approvals import ApprovalStatus, ApprovalSystem, ApprovalType
from backend.workflows.engine import WorkflowEngine
from backend.workflows.events import EventDispatcher, WorkflowEventType
from backend.workflows.states import (
    STATE_HANDLERS,
    ContractState,
    StateHandler,
)

__all__ = [
    "WorkflowEngine",
    "ContractState",
    "StateHandler",
    "STATE_HANDLERS",
    "ApprovalSystem",
    "ApprovalStatus",
    "ApprovalType",
    "EventDispatcher",
    "WorkflowEventType",
]
