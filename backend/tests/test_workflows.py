"""Unit tests for the Phase 5D contract workflow engine.

These tests exercise WorkflowEngine, state handlers, ApprovalSystem, and
EventDispatcher **without** requiring a live MongoDB connection.  All
database and module calls are mocked via ``unittest.mock``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.workflows.states import (
    STATE_HANDLERS,
    ContractState,
    CancelledStateHandler,
    CompletedStateHandler,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contract(
    uid: int = 1,
    contract_code: str = "CNT-001",
    state: str = "DRAFT",
    enabled_modules: list | None = None,
) -> MagicMock:
    """Return a lightweight mock that behaves like a Contract document."""
    c = MagicMock()
    c.uid = uid
    c.contract_code = contract_code
    c.workflow_state = state
    c.workflow_metadata = {}
    c.state_changed_at = None
    c.state_changed_by = None
    c.enabled_modules = enabled_modules or []
    c.project_id = 42
    c.contract_value = 1000.0
    c.created_by_admin_id = 99
    c.save = AsyncMock()
    return c


# ---------------------------------------------------------------------------
# STATE_HANDLERS registry
# ---------------------------------------------------------------------------


class TestStateHandlersRegistry:
    def test_all_states_have_handlers(self):
        for state in ContractState:
            assert state in STATE_HANDLERS, f"Missing handler for {state}"

    def test_handler_state_attribute_matches_key(self):
        for state, handler in STATE_HANDLERS.items():
            assert handler.state == state

    def test_terminal_states_have_no_transitions(self):
        for state in (ContractState.COMPLETED, ContractState.CANCELLED):
            handler = STATE_HANDLERS[state]
            assert handler.get_allowed_transitions() == []

    def test_non_terminal_states_have_transitions(self):
        non_terminal = [
            ContractState.DRAFT,
            ContractState.PENDING_APPROVAL,
            ContractState.ACTIVE,
            ContractState.SUSPENDED,
        ]
        for state in non_terminal:
            handler = STATE_HANDLERS[state]
            assert len(handler.get_allowed_transitions()) > 0, (
                f"{state} should have at least one allowed transition"
            )


# ---------------------------------------------------------------------------
# Transition validation
# ---------------------------------------------------------------------------


class TestStateTransitions:
    def test_draft_can_go_to_pending_approval(self):
        handler = STATE_HANDLERS[ContractState.DRAFT]
        assert ContractState.PENDING_APPROVAL in handler.get_allowed_transitions()

    def test_draft_can_be_cancelled(self):
        handler = STATE_HANDLERS[ContractState.DRAFT]
        assert ContractState.CANCELLED in handler.get_allowed_transitions()

    def test_draft_cannot_go_directly_to_active(self):
        handler = STATE_HANDLERS[ContractState.DRAFT]
        assert ContractState.ACTIVE not in handler.get_allowed_transitions()

    def test_pending_approval_can_go_to_active(self):
        handler = STATE_HANDLERS[ContractState.PENDING_APPROVAL]
        assert ContractState.ACTIVE in handler.get_allowed_transitions()

    def test_pending_approval_can_go_back_to_draft(self):
        handler = STATE_HANDLERS[ContractState.PENDING_APPROVAL]
        assert ContractState.DRAFT in handler.get_allowed_transitions()

    def test_active_can_be_suspended(self):
        handler = STATE_HANDLERS[ContractState.ACTIVE]
        assert ContractState.SUSPENDED in handler.get_allowed_transitions()

    def test_active_can_be_completed(self):
        handler = STATE_HANDLERS[ContractState.ACTIVE]
        assert ContractState.COMPLETED in handler.get_allowed_transitions()

    def test_suspended_can_resume_to_active(self):
        handler = STATE_HANDLERS[ContractState.SUSPENDED]
        assert ContractState.ACTIVE in handler.get_allowed_transitions()

    def test_completed_has_no_transitions(self):
        assert STATE_HANDLERS[ContractState.COMPLETED].get_allowed_transitions() == []

    def test_cancelled_has_no_transitions(self):
        assert STATE_HANDLERS[ContractState.CANCELLED].get_allowed_transitions() == []


# ---------------------------------------------------------------------------
# WorkflowEngine.transition
# ---------------------------------------------------------------------------


class TestWorkflowEngineTransition:
    @pytest.mark.asyncio
    async def test_successful_transition_updates_contract(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="DRAFT")

        with (
            patch("backend.workflows.engine.WorkflowEngine._record_history", new=AsyncMock()),
            patch("backend.workflows.engine.WorkflowEngine._dispatch_state_changed", new=AsyncMock()),
        ):
            result = await WorkflowEngine.transition(
                contract=contract,
                target_state=ContractState.PENDING_APPROVAL,
                changed_by=7,
                reason="Ready for review",
            )

        assert result["success"] is True
        assert result["from_state"] == "DRAFT"
        assert result["to_state"] == "PENDING_APPROVAL"
        assert contract.workflow_state == "PENDING_APPROVAL"
        assert contract.state_changed_by == 7
        contract.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disallowed_transition_returns_error(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="DRAFT")

        result = await WorkflowEngine.transition(
            contract=contract,
            target_state=ContractState.ACTIVE,  # not allowed from DRAFT
        )

        assert result["success"] is False
        assert "not allowed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_transition_records_history(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="DRAFT")
        record_mock = AsyncMock()
        dispatch_mock = AsyncMock()

        with (
            patch("backend.workflows.engine.WorkflowEngine._record_history", new=record_mock),
            patch("backend.workflows.engine.WorkflowEngine._dispatch_state_changed", new=dispatch_mock),
        ):
            await WorkflowEngine.transition(
                contract=contract,
                target_state=ContractState.PENDING_APPROVAL,
            )

        record_mock.assert_awaited_once()
        dispatch_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_transition_from_terminal_state_fails(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="COMPLETED")

        result = await WorkflowEngine.transition(
            contract=contract,
            target_state=ContractState.ACTIVE,
        )

        assert result["success"] is False


# ---------------------------------------------------------------------------
# WorkflowEngine.get_available_transitions
# ---------------------------------------------------------------------------


class TestGetAvailableTransitions:
    def test_draft_contract_transitions(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="DRAFT")
        transitions = WorkflowEngine.get_available_transitions(contract)
        assert ContractState.PENDING_APPROVAL in transitions
        assert ContractState.CANCELLED in transitions

    def test_completed_contract_no_transitions(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="COMPLETED")
        assert WorkflowEngine.get_available_transitions(contract) == []

    def test_cancelled_contract_no_transitions(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="CANCELLED")
        assert WorkflowEngine.get_available_transitions(contract) == []


# ---------------------------------------------------------------------------
# WorkflowEngine.validate_current_state
# ---------------------------------------------------------------------------


class TestValidateCurrentState:
    def test_draft_with_required_fields_is_valid(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="DRAFT")
        result = WorkflowEngine.validate_current_state(contract)
        assert result["is_valid"] is True
        assert result["state"] == "DRAFT"

    def test_draft_missing_contract_code_is_invalid(self):
        from backend.workflows.engine import WorkflowEngine

        contract = _make_contract(state="DRAFT")
        contract.contract_code = None
        result = WorkflowEngine.validate_current_state(contract)
        assert result["is_valid"] is False
        assert any("contract_code" in issue for issue in result["issues"])


# ---------------------------------------------------------------------------
# Module initialization on ACTIVE
# ---------------------------------------------------------------------------


class TestModuleInitializationOnActive:
    @pytest.mark.asyncio
    async def test_active_on_enter_initialises_enabled_modules(self):
        handler = STATE_HANDLERS[ContractState.ACTIVE]
        contract = _make_contract(enabled_modules=["employee", "inventory"])

        mock_module = MagicMock()
        mock_module.initialize = AsyncMock(return_value={"status": "ok"})

        with patch("backend.modules.registry.ModuleRegistry.get_module", return_value=mock_module):
            result = await handler.on_enter(contract, {})

        assert "module_init_results" in result
        assert "employee" in result["module_init_results"]
        assert "inventory" in result["module_init_results"]

    @pytest.mark.asyncio
    async def test_active_on_enter_handles_missing_module_gracefully(self):
        handler = STATE_HANDLERS[ContractState.ACTIVE]
        contract = _make_contract(enabled_modules=["nonexistent"])

        with patch("backend.modules.registry.ModuleRegistry.get_module", return_value=None):
            result = await handler.on_enter(contract, {})

        assert result["module_init_results"]["nonexistent"]["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_active_on_enter_handles_module_exception(self):
        handler = STATE_HANDLERS[ContractState.ACTIVE]
        contract = _make_contract(enabled_modules=["broken"])

        mock_module = MagicMock()
        mock_module.initialize = AsyncMock(side_effect=RuntimeError("DB error"))

        with patch("backend.modules.registry.ModuleRegistry.get_module", return_value=mock_module):
            result = await handler.on_enter(contract, {})

        assert result["module_init_results"]["broken"]["status"] == "failed"
        assert "DB error" in result["module_init_results"]["broken"]["error"]


# ---------------------------------------------------------------------------
# Module cleanup on COMPLETED / CANCELLED
# ---------------------------------------------------------------------------


class TestModuleCleanupOnTerminal:
    @pytest.mark.asyncio
    async def test_completed_on_enter_cleans_up_modules(self):
        handler = STATE_HANDLERS[ContractState.COMPLETED]
        contract = _make_contract(enabled_modules=["vehicle"])

        mock_module = MagicMock()
        mock_module.cleanup = AsyncMock(return_value=True)

        with patch("backend.modules.registry.ModuleRegistry.get_module", return_value=mock_module):
            result = await handler.on_enter(contract, {})

        assert "module_cleanup_results" in result
        assert result["module_cleanup_results"]["vehicle"]["status"] == "cleaned_up"

    @pytest.mark.asyncio
    async def test_cancelled_on_enter_cleans_up_modules(self):
        handler = STATE_HANDLERS[ContractState.CANCELLED]
        contract = _make_contract(enabled_modules=["employee"])

        mock_module = MagicMock()
        mock_module.cleanup = AsyncMock(return_value=True)

        with patch("backend.modules.registry.ModuleRegistry.get_module", return_value=mock_module):
            result = await handler.on_enter(contract, {})

        assert "module_cleanup_results" in result
        assert result["module_cleanup_results"]["employee"]["status"] == "cleaned_up"


# ---------------------------------------------------------------------------
# ApprovalSystem
# ---------------------------------------------------------------------------


class TestApprovalSystem:
    @pytest.mark.asyncio
    async def test_create_approval_request_returns_pending_status(self):
        from backend.workflows.approvals import ApprovalSystem, ApprovalType

        contract = _make_contract()

        mock_approval = MagicMock()
        mock_approval.insert = AsyncMock()

        with (
            patch(
                "backend.workflows.approvals.ApprovalRequest",
                return_value=mock_approval,
            ),
            patch("backend.workflows.approvals.ApprovalSystem._dispatch_event", new=AsyncMock()),
        ):
            result = await ApprovalSystem.create_approval_request(
                contract=contract,
                approval_type=ApprovalType.CONTRACT_ACTIVATION,
                requested_by=5,
                required_approvers=[10, 11],
            )

        assert result["status"] == "PENDING"
        assert result["approval_type"] == "contract_activation"
        assert 10 in result["required_approvers"]

    @pytest.mark.asyncio
    async def test_reject_returns_rejected_status(self):
        from backend.workflows.approvals import ApprovalSystem, ApprovalStatus, ApprovalType

        contract = _make_contract()

        mock_approval = MagicMock()
        mock_approval.status = ApprovalStatus.PENDING.value
        mock_approval.save = AsyncMock()

        with (
            patch(
                "backend.workflows.approvals.ApprovalRequest.find_one",
                new=AsyncMock(return_value=mock_approval),
            ),
            patch("backend.workflows.approvals.ApprovalSystem._dispatch_event", new=AsyncMock()),
        ):
            result = await ApprovalSystem.reject(
                contract=contract,
                approval_type=ApprovalType.CONTRACT_ACTIVATION,
                rejector_id=99,
                reason="Missing documentation",
            )

        assert result["success"] is True
        assert result["approval_status"] == "REJECTED"
        assert "Missing documentation" in result["reason"]

    @pytest.mark.asyncio
    async def test_reject_no_pending_request_returns_error(self):
        from backend.workflows.approvals import ApprovalSystem, ApprovalType

        contract = _make_contract()

        with patch(
            "backend.workflows.approvals.ApprovalRequest.find_one",
            new=AsyncMock(return_value=None),
        ):
            result = await ApprovalSystem.reject(
                contract=contract,
                approval_type=ApprovalType.CONTRACT_ACTIVATION,
                rejector_id=99,
                reason="Test",
            )

        assert result["success"] is False
        assert "No pending" in result["error"]


# ---------------------------------------------------------------------------
# EventDispatcher
# ---------------------------------------------------------------------------


class TestEventDispatcher:
    @pytest.mark.asyncio
    async def test_register_and_receive_event(self):
        from backend.workflows.events import EventDispatcher, WorkflowEventType

        received: list = []

        async def handler(event_type, payload):
            received.append((event_type, payload))

        EventDispatcher.register_handler(WorkflowEventType.STATE_CHANGED, handler)

        with patch(
            "backend.workflows.events.EventDispatcher._log_event",
            new=AsyncMock(),
        ):
            await EventDispatcher.dispatch(
                WorkflowEventType.STATE_CHANGED, {"contract_id": 1}
            )

        EventDispatcher.unregister_handler(WorkflowEventType.STATE_CHANGED, handler)
        assert len(received) == 1
        assert received[0][0] == WorkflowEventType.STATE_CHANGED

    @pytest.mark.asyncio
    async def test_unregister_handler_stops_delivery(self):
        from backend.workflows.events import EventDispatcher, WorkflowEventType

        received: list = []

        async def handler(event_type, payload):
            received.append(event_type)

        EventDispatcher.register_handler(WorkflowEventType.VALIDATION_FAILED, handler)
        EventDispatcher.unregister_handler(WorkflowEventType.VALIDATION_FAILED, handler)

        with patch(
            "backend.workflows.events.EventDispatcher._log_event",
            new=AsyncMock(),
        ):
            await EventDispatcher.dispatch(
                WorkflowEventType.VALIDATION_FAILED, {}
            )

        assert received == []

    @pytest.mark.asyncio
    async def test_wildcard_handler_receives_all_events(self):
        from backend.workflows.events import EventDispatcher, WorkflowEventType

        received: list = []

        async def wildcard(event_type, payload):
            received.append(event_type)

        EventDispatcher.register_handler(None, wildcard)

        with patch(
            "backend.workflows.events.EventDispatcher._log_event",
            new=AsyncMock(),
        ):
            await EventDispatcher.dispatch(WorkflowEventType.MODULE_INITIALIZED, {})
            await EventDispatcher.dispatch(WorkflowEventType.MODULE_FAILED, {})

        EventDispatcher.unregister_handler(None, wildcard)
        assert WorkflowEventType.MODULE_INITIALIZED in received
        assert WorkflowEventType.MODULE_FAILED in received

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_prevent_other_handlers(self):
        from backend.workflows.events import EventDispatcher, WorkflowEventType

        results: list = []

        async def bad_handler(event_type, payload):
            raise RuntimeError("boom")

        async def good_handler(event_type, payload):
            results.append("ok")

        EventDispatcher.register_handler(WorkflowEventType.APPROVAL_REQUESTED, bad_handler)
        EventDispatcher.register_handler(WorkflowEventType.APPROVAL_REQUESTED, good_handler)

        with patch(
            "backend.workflows.events.EventDispatcher._log_event",
            new=AsyncMock(),
        ):
            await EventDispatcher.dispatch(WorkflowEventType.APPROVAL_REQUESTED, {})

        EventDispatcher.unregister_handler(WorkflowEventType.APPROVAL_REQUESTED, bad_handler)
        EventDispatcher.unregister_handler(WorkflowEventType.APPROVAL_REQUESTED, good_handler)
        assert "ok" in results


# ---------------------------------------------------------------------------
# Contract model workflow fields
# ---------------------------------------------------------------------------


class TestContractWorkflowFields:
    def test_workflow_fields_exist(self):
        from backend.models.projects import Contract

        fields = Contract.model_fields
        assert "workflow_state" in fields
        assert "workflow_metadata" in fields
        assert "state_changed_at" in fields
        assert "state_changed_by" in fields

    def test_workflow_state_defaults_to_draft(self):
        from backend.models.projects import Contract

        field = Contract.model_fields["workflow_state"]
        assert field.default == "DRAFT"

    def test_workflow_metadata_defaults_to_empty_dict(self):
        from backend.models.projects import Contract

        field = Contract.model_fields["workflow_metadata"]
        default = (
            field.default_factory() if field.default_factory is not None else field.default
        )
        assert default == {}
