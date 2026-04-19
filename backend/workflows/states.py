"""
Contract state definitions and handlers for the Phase 5D workflow engine.

Each state has an associated StateHandler that defines:
- Allowed transitions out of the state
- Entry / exit actions
- Validation logic
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# ContractState enum
# ---------------------------------------------------------------------------


class ContractState(str, Enum):
    """All possible lifecycle states for a Contract document."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Abstract StateHandler
# ---------------------------------------------------------------------------


class StateHandler(ABC):
    """
    Abstract base class that encapsulates the behaviour of one contract state.

    Sub-classes implement on_enter / on_exit hooks and declare which
    transitions are valid from this state.
    """

    state: ContractState

    @abstractmethod
    def get_allowed_transitions(self) -> List[ContractState]:
        """Return the states that are reachable from this one."""

    async def on_enter(self, contract: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called when a contract transitions *into* this state.

        Returns a metadata dict that is merged into the contract's
        workflow_metadata field.
        """
        return {}

    async def on_exit(self, contract: Any, context: Dict[str, Any]) -> None:
        """Called when a contract transitions *out of* this state."""

    def validate(self, contract: Any) -> Dict[str, Any]:
        """
        Validate that the contract satisfies the requirements of this state.

        Returns ``{"is_valid": True, "issues": []}`` on success, or
        ``{"is_valid": False, "issues": ["reason …"]}`` on failure.
        """
        return {"is_valid": True, "issues": []}


# ---------------------------------------------------------------------------
# Concrete handlers
# ---------------------------------------------------------------------------


class DraftStateHandler(StateHandler):
    """Contract is being prepared; all fields are still editable."""

    state = ContractState.DRAFT

    def get_allowed_transitions(self) -> List[ContractState]:
        return [ContractState.PENDING_APPROVAL, ContractState.CANCELLED]

    def validate(self, contract: Any) -> Dict[str, Any]:
        issues: List[str] = []
        if not getattr(contract, "contract_code", None):
            issues.append("contract_code is required")
        if not getattr(contract, "project_id", None):
            issues.append("project_id is required")
        return {"is_valid": len(issues) == 0, "issues": issues}


class PendingApprovalStateHandler(StateHandler):
    """Contract has been submitted for review by an approver."""

    state = ContractState.PENDING_APPROVAL

    def get_allowed_transitions(self) -> List[ContractState]:
        return [ContractState.ACTIVE, ContractState.DRAFT, ContractState.CANCELLED]

    def validate(self, contract: Any) -> Dict[str, Any]:
        issues: List[str] = []
        if not getattr(contract, "contract_value", None):
            issues.append("contract_value must be set before submitting for approval")
        return {"is_valid": len(issues) == 0, "issues": issues}


class ActiveStateHandler(StateHandler):
    """Contract is approved and running; modules are initialised on entry."""

    state = ContractState.ACTIVE

    def get_allowed_transitions(self) -> List[ContractState]:
        return [ContractState.SUSPENDED, ContractState.COMPLETED, ContractState.CANCELLED]

    async def on_enter(self, contract: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Initialise all enabled modules for the contract."""
        from backend.modules.registry import ModuleRegistry

        init_results: Dict[str, Any] = {}
        enabled: List[str] = getattr(contract, "enabled_modules", []) or []

        for module_name in enabled:
            module = ModuleRegistry.get_module(module_name)
            if module is None:
                init_results[module_name] = {"status": "not_found"}
                continue
            try:
                result = await module.initialize(contract)
                init_results[module_name] = {"status": "initialized", **result}
            except Exception as exc:  # noqa: BLE001
                init_results[module_name] = {"status": "failed", "error": str(exc)}

        return {"module_init_results": init_results}


class SuspendedStateHandler(StateHandler):
    """Contract is temporarily paused."""

    state = ContractState.SUSPENDED

    def get_allowed_transitions(self) -> List[ContractState]:
        return [ContractState.ACTIVE, ContractState.CANCELLED]


class CompletedStateHandler(StateHandler):
    """Contract has finished successfully — terminal state."""

    state = ContractState.COMPLETED

    def get_allowed_transitions(self) -> List[ContractState]:
        return []  # terminal

    async def on_enter(self, contract: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up all enabled modules when the contract completes."""
        from backend.modules.registry import ModuleRegistry

        cleanup_results: Dict[str, Any] = {}
        enabled: List[str] = getattr(contract, "enabled_modules", []) or []

        for module_name in enabled:
            module = ModuleRegistry.get_module(module_name)
            if module is None:
                cleanup_results[module_name] = {"status": "not_found"}
                continue
            try:
                success = await module.cleanup(contract)
                cleanup_results[module_name] = {
                    "status": "cleaned_up" if success else "cleanup_failed"
                }
            except Exception as exc:  # noqa: BLE001
                cleanup_results[module_name] = {"status": "error", "error": str(exc)}

        return {"module_cleanup_results": cleanup_results}


class CancelledStateHandler(StateHandler):
    """Contract was terminated early — terminal state."""

    state = ContractState.CANCELLED

    def get_allowed_transitions(self) -> List[ContractState]:
        return []  # terminal

    async def on_enter(self, contract: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up all enabled modules when the contract is cancelled."""
        from backend.modules.registry import ModuleRegistry

        cleanup_results: Dict[str, Any] = {}
        enabled: List[str] = getattr(contract, "enabled_modules", []) or []

        for module_name in enabled:
            module = ModuleRegistry.get_module(module_name)
            if module is None:
                cleanup_results[module_name] = {"status": "not_found"}
                continue
            try:
                success = await module.cleanup(contract)
                cleanup_results[module_name] = {
                    "status": "cleaned_up" if success else "cleanup_failed"
                }
            except Exception as exc:  # noqa: BLE001
                cleanup_results[module_name] = {"status": "error", "error": str(exc)}

        return {"module_cleanup_results": cleanup_results}


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

STATE_HANDLERS: Dict[ContractState, StateHandler] = {
    ContractState.DRAFT: DraftStateHandler(),
    ContractState.PENDING_APPROVAL: PendingApprovalStateHandler(),
    ContractState.ACTIVE: ActiveStateHandler(),
    ContractState.SUSPENDED: SuspendedStateHandler(),
    ContractState.COMPLETED: CompletedStateHandler(),
    ContractState.CANCELLED: CancelledStateHandler(),
}
