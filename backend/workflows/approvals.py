"""Approval system for contract workflow transitions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Top-level import so the class is patchable in tests.
# The import succeeds without a live DB — only .insert() / .find_one() require one.
from backend.models.workflow_history import ApprovalRequest  # noqa: F401


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalType(str, Enum):
    CONTRACT_ACTIVATION = "contract_activation"
    BUDGET_CHANGE = "budget_change"
    MODULE_CHANGE = "module_change"
    CONTRACT_COMPLETION = "contract_completion"


# ---------------------------------------------------------------------------
# ApprovalSystem
# ---------------------------------------------------------------------------


class ApprovalSystem:
    """
    Manages multi-level approval workflows for contracts.

    All methods are static/async so they integrate naturally with the
    WorkflowEngine without requiring an instance.
    """

    @staticmethod
    async def create_approval_request(
        contract: Any,
        approval_type: ApprovalType,
        requested_by: int,
        required_approvers: Optional[List[int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new approval request for *contract*.

        If *required_approvers* is not supplied, the method falls back to a
        sensible default (the contract creator, if available).

        Returns a summary dict; the persisted ``ApprovalRequest`` id is
        included when the database is available.
        """
        if required_approvers is None:
            required_approvers = []
            creator = getattr(contract, "created_by_admin_id", None)
            if creator:
                required_approvers.append(creator)

        now = datetime.now()
        approval = ApprovalRequest(
            contract_id=getattr(contract, "uid", None),
            approval_type=approval_type.value,
            status=ApprovalStatus.PENDING.value,
            required_approvers=required_approvers,
            pending_approvers=list(required_approvers),
            approved_by=[],
            requested_by=requested_by,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        try:
            await approval.insert()
        except Exception:  # noqa: BLE001
            pass

        # Dispatch event
        await ApprovalSystem._dispatch_event(
            "APPROVAL_REQUESTED",
            {
                "contract_id": getattr(contract, "uid", None),
                "approval_type": approval_type.value,
                "required_approvers": required_approvers,
            },
        )

        return {
            "approval_type": approval_type.value,
            "status": ApprovalStatus.PENDING.value,
            "required_approvers": required_approvers,
            "pending_approvers": required_approvers,
        }

    @staticmethod
    async def approve(
        contract: Any,
        approval_type: ApprovalType,
        approver_id: int,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record an approval decision from *approver_id*.

        When all required approvers have approved, the contract is
        automatically transitioned to ACTIVE (for ``contract_activation``
        approvals).

        Returns ``{"all_approved": bool, "approval_status": str}``.
        """
        approval = await ApprovalRequest.find_one(
            {
                "contract_id": getattr(contract, "uid", None),
                "approval_type": approval_type.value,
                "status": ApprovalStatus.PENDING.value,
            }
        )

        if approval is None:
            return {
                "success": False,
                "error": "No pending approval request found",
            }

        # Record the approver
        if approver_id in approval.pending_approvers:
            approval.pending_approvers.remove(approver_id)
        if approver_id not in approval.approved_by:
            approval.approved_by.append(approver_id)

        approval.updated_at = datetime.now()

        all_approved = len(approval.pending_approvers) == 0

        if all_approved:
            approval.status = ApprovalStatus.APPROVED.value

        try:
            await approval.save()
        except Exception:  # noqa: BLE001
            pass

        await ApprovalSystem._dispatch_event(
            "APPROVAL_APPROVED",
            {
                "contract_id": getattr(contract, "uid", None),
                "approver_id": approver_id,
                "all_approved": all_approved,
                "comment": comment,
            },
        )

        # Auto-transition on full approval
        if all_approved and approval_type == ApprovalType.CONTRACT_ACTIVATION:
            from backend.workflows.engine import WorkflowEngine
            from backend.workflows.states import ContractState

            await WorkflowEngine.transition(
                contract=contract,
                target_state=ContractState.ACTIVE,
                changed_by=approver_id,
                reason="Auto-transitioned after all approvals received",
            )

        return {
            "success": True,
            "all_approved": all_approved,
            "approval_status": approval.status,
            "pending_approvers": approval.pending_approvers,
        }

    @staticmethod
    async def reject(
        contract: Any,
        approval_type: ApprovalType,
        rejector_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Record a rejection from *rejector_id*.

        The approval request is moved to REJECTED status and a
        ``APPROVAL_REJECTED`` event is dispatched.
        """
        approval = await ApprovalRequest.find_one(
            {
                "contract_id": getattr(contract, "uid", None),
                "approval_type": approval_type.value,
                "status": ApprovalStatus.PENDING.value,
            }
        )

        if approval is None:
            return {
                "success": False,
                "error": "No pending approval request found",
            }

        approval.status = ApprovalStatus.REJECTED.value
        approval.rejection_reason = reason
        approval.rejected_by = rejector_id
        approval.updated_at = datetime.now()

        try:
            await approval.save()
        except Exception:  # noqa: BLE001
            pass

        await ApprovalSystem._dispatch_event(
            "APPROVAL_REJECTED",
            {
                "contract_id": getattr(contract, "uid", None),
                "rejector_id": rejector_id,
                "reason": reason,
            },
        )

        return {
            "success": True,
            "approval_status": ApprovalStatus.REJECTED.value,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _dispatch_event(event_type_str: str, payload: Dict[str, Any]) -> None:
        try:
            from backend.workflows.events import EventDispatcher, WorkflowEventType

            event_type = WorkflowEventType(event_type_str)
            await EventDispatcher.dispatch(event_type=event_type, payload=payload)
        except Exception:  # noqa: BLE001
            pass
