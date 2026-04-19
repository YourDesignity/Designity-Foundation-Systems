"""Workflow orchestration engine for contract lifecycle management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.workflows.states import STATE_HANDLERS, ContractState


class WorkflowEngine:
    """
    Static-method facade for contract state management.

    All public methods are ``async`` so they can be awaited from FastAPI
    route handlers or background tasks without further wrapping.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    async def transition(
        contract: Any,
        target_state: ContractState,
        context: Optional[Dict[str, Any]] = None,
        changed_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate and execute a state transition for *contract*.

        Steps
        -----
        1. Resolve the current state handler.
        2. Check that *target_state* is in the handler's allowed transitions.
        3. Call ``on_exit`` on the current handler.
        4. Call ``on_enter`` on the target handler.
        5. Persist the new state fields on the contract.
        6. Record a :class:`WorkflowHistory` entry.
        7. Dispatch a ``STATE_CHANGED`` event.

        Returns a result dict with ``success``, ``from_state``, ``to_state``,
        and any metadata produced by the target handler's ``on_enter``.
        """
        context = context or {}
        current_state_str: str = getattr(contract, "workflow_state", ContractState.DRAFT)

        try:
            current_state = ContractState(current_state_str)
        except ValueError:
            current_state = ContractState.DRAFT

        current_handler = STATE_HANDLERS.get(current_state)
        if current_handler is None:
            return {
                "success": False,
                "error": f"No handler registered for state '{current_state}'",
            }

        allowed = current_handler.get_allowed_transitions()
        if target_state not in allowed:
            return {
                "success": False,
                "error": (
                    f"Transition from {current_state} to {target_state} is not allowed. "
                    f"Allowed: {[s.value for s in allowed]}"
                ),
            }

        target_handler = STATE_HANDLERS.get(target_state)
        if target_handler is None:
            return {
                "success": False,
                "error": f"No handler registered for target state '{target_state}'",
            }

        # Exit current state
        await current_handler.on_exit(contract, context)

        # Enter target state
        enter_metadata = await target_handler.on_enter(contract, context)

        # Update contract fields
        contract.workflow_state = target_state.value
        contract.state_changed_at = datetime.now()
        contract.state_changed_by = changed_by

        existing_meta: Dict[str, Any] = getattr(contract, "workflow_metadata", {}) or {}
        existing_meta.update(enter_metadata)
        contract.workflow_metadata = existing_meta

        # Persist (Beanie document)
        if hasattr(contract, "save"):
            await contract.save()

        # Record history
        await WorkflowEngine._record_history(
            contract=contract,
            from_state=current_state,
            to_state=target_state,
            changed_by=changed_by,
            reason=reason,
            metadata=enter_metadata,
        )

        # Dispatch event
        await WorkflowEngine._dispatch_state_changed(
            contract=contract,
            from_state=current_state,
            to_state=target_state,
            changed_by=changed_by,
            context=context,
        )

        return {
            "success": True,
            "from_state": current_state.value,
            "to_state": target_state.value,
            "metadata": enter_metadata,
        }

    @staticmethod
    def get_available_transitions(contract: Any) -> List[ContractState]:
        """Return the list of states reachable from the contract's current state."""
        current_state_str: str = getattr(contract, "workflow_state", ContractState.DRAFT)
        try:
            current_state = ContractState(current_state_str)
        except ValueError:
            current_state = ContractState.DRAFT

        handler = STATE_HANDLERS.get(current_state)
        if handler is None:
            return []
        return handler.get_allowed_transitions()

    @staticmethod
    def validate_current_state(contract: Any) -> Dict[str, Any]:
        """
        Validate whether *contract* satisfies the requirements of its current
        workflow state.

        Returns ``{"is_valid": bool, "state": str, "issues": list}``.
        """
        current_state_str: str = getattr(contract, "workflow_state", ContractState.DRAFT)
        try:
            current_state = ContractState(current_state_str)
        except ValueError:
            current_state = ContractState.DRAFT

        handler = STATE_HANDLERS.get(current_state)
        if handler is None:
            return {
                "is_valid": False,
                "state": current_state_str,
                "issues": [f"No handler for state '{current_state_str}'"],
            }

        result = handler.validate(contract)
        return {"state": current_state.value, **result}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _record_history(
        contract: Any,
        from_state: ContractState,
        to_state: ContractState,
        changed_by: Optional[int],
        reason: Optional[str],
        metadata: Dict[str, Any],
    ) -> None:
        """Persist a WorkflowHistory document (best-effort; never raises)."""
        try:
            from backend.models.workflow_history import WorkflowHistory

            entry = WorkflowHistory(
                contract_id=getattr(contract, "uid", None),
                from_state=from_state.value,
                to_state=to_state.value,
                changed_by=changed_by,
                reason=reason,
                metadata=metadata,
                timestamp=datetime.now(),
            )
            await entry.insert()
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    async def _dispatch_state_changed(
        contract: Any,
        from_state: ContractState,
        to_state: ContractState,
        changed_by: Optional[int],
        context: Dict[str, Any],
    ) -> None:
        """Dispatch a STATE_CHANGED event (best-effort; never raises)."""
        try:
            from backend.workflows.events import EventDispatcher, WorkflowEventType

            await EventDispatcher.dispatch(
                event_type=WorkflowEventType.STATE_CHANGED,
                payload={
                    "contract_id": getattr(contract, "uid", None),
                    "contract_code": getattr(contract, "contract_code", None),
                    "from_state": from_state.value,
                    "to_state": to_state.value,
                    "changed_by": changed_by,
                    **context,
                },
            )
        except Exception:  # noqa: BLE001
            pass
