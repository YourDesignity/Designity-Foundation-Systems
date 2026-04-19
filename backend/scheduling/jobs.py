"""
Job execution implementations for Phase 5E scheduled tasks.

Each public method of JobExecutor corresponds to a ScheduleType value and is
called by SchedulingEngine.process_due_jobs() when a job becomes due.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from backend.modules.registry import ModuleRegistry
from backend.scheduling.notifications import NotificationSystem
from backend.workflows.approvals import ApprovalSystem, ApprovalType
from backend.workflows.engine import WorkflowEngine
from backend.workflows.states import ContractState


class JobExecutor:
    """
    Async implementations for every built-in job type.

    All methods are static so the engine does not need to manage executor
    instances.  Each method is responsible for:
    1. Loading the target document from MongoDB.
    2. Performing the business action.
    3. Dispatching notifications where appropriate.

    Database and external-service failures are propagated as exceptions so
    the calling engine can update the job's retry_count / status correctly.
    """

    # ------------------------------------------------------------------
    # Contract lifecycle jobs
    # ------------------------------------------------------------------

    @staticmethod
    async def execute_contract_activation(contract_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Activate a contract on its start_date.

        Loads the contract, verifies it is still in DRAFT or PENDING_APPROVAL,
        then delegates the state transition to WorkflowEngine.
        """
        contract = await JobExecutor._load_contract(contract_id)
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not found"}

        current_state = getattr(contract, "workflow_state", "DRAFT")
        if current_state not in ("DRAFT", "PENDING_APPROVAL"):
            return {
                "success": False,
                "error": f"Contract {contract_id} is in state '{current_state}', skipping activation",
            }

        result = await WorkflowEngine.transition(
            contract=contract,
            target_state=ContractState.ACTIVE,
            reason="Automated activation on start_date",
        )

        if result.get("success"):
            await NotificationSystem.send_notification(
                notification_type="contract_activated",
                recipient_id=getattr(contract, "created_by_admin_id", 0) or 0,
                channel="in_app",
                subject=f"Contract {getattr(contract, 'contract_code', contract_id)} Activated",
                body=f"Contract has been automatically activated.",
                metadata={"contract_id": contract_id},
            )

        return result

    @staticmethod
    async def execute_expiry_warning(
        contract_id: int,
        days_remaining: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send expiry warning notifications for a contract approaching its end_date.
        """
        contract = await JobExecutor._load_contract(contract_id)
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not found"}

        current_state = getattr(contract, "workflow_state", "DRAFT")
        if current_state != "ACTIVE":
            return {
                "success": False,
                "error": f"Contract {contract_id} is not ACTIVE (state='{current_state}'), skipping warning",
            }

        await NotificationSystem.send_expiry_warning(contract, days_remaining)

        return {"success": True, "contract_id": contract_id, "days_remaining": days_remaining}

    @staticmethod
    async def execute_auto_completion(contract_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Auto-complete a contract that has reached its end_date.
        """
        contract = await JobExecutor._load_contract(contract_id)
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not found"}

        current_state = getattr(contract, "workflow_state", "DRAFT")
        if current_state != "ACTIVE":
            return {
                "success": False,
                "error": f"Contract {contract_id} is not ACTIVE (state='{current_state}'), skipping completion",
            }

        result = await WorkflowEngine.transition(
            contract=contract,
            target_state=ContractState.COMPLETED,
            reason="Automated completion on end_date",
        )

        if result.get("success"):
            await NotificationSystem.send_completion_notification(contract)

        return result

    # ------------------------------------------------------------------
    # Cost & financial jobs
    # ------------------------------------------------------------------

    @staticmethod
    async def execute_cost_calculation(
        contract_id: int,
        month: int,
        year: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run calculate_cost on every enabled module for *contract_id* and store
        the aggregated results in contract.workflow_metadata.
        """
        contract = await JobExecutor._load_contract(contract_id)
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not found"}

        enabled_modules = getattr(contract, "enabled_modules", []) or []
        results: Dict[str, Any] = {}
        total_cost = 0.0

        for module_name in enabled_modules:
            module = ModuleRegistry.get_module(module_name)
            if module is None:
                results[module_name] = {"status": "not_found"}
                continue
            try:
                calc = await module.calculate_cost(contract, month, year)
                results[module_name] = calc
                total_cost += float(calc.get("total_cost", 0))
            except Exception as exc:  # noqa: BLE001
                results[module_name] = {"status": "failed", "error": str(exc)}

        # Persist summary in workflow_metadata
        meta = getattr(contract, "workflow_metadata", {}) or {}
        meta[f"cost_{year}_{month:02d}"] = {
            "month": month,
            "year": year,
            "total_cost": total_cost,
            "by_module": results,
            "calculated_at": datetime.now().isoformat(),
        }
        contract.workflow_metadata = meta
        if hasattr(contract, "save"):
            await contract.save()

        return {
            "success": True,
            "contract_id": contract_id,
            "month": month,
            "year": year,
            "total_cost": total_cost,
            "by_module": results,
        }

    # ------------------------------------------------------------------
    # Renewal & payment jobs
    # ------------------------------------------------------------------

    @staticmethod
    async def execute_renewal_request(contract_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initiate a renewal workflow for a contract approaching expiry.

        Creates an approval request via ApprovalSystem so stakeholders can
        review and approve / reject the renewal before the contract expires.
        """
        contract = await JobExecutor._load_contract(contract_id)
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not found"}

        created_by: int = getattr(contract, "created_by_admin_id", 0) or 0

        approval_result = await ApprovalSystem.create_approval_request(
            contract=contract,
            approval_type=ApprovalType.CONTRACT_ACTIVATION,
            requested_by=created_by,
            required_approvers=[created_by] if created_by else [],
            metadata={"reason": "automated_renewal_request"},
        )

        await NotificationSystem.send_renewal_reminder(contract)

        return {
            "success": True,
            "contract_id": contract_id,
            "approval_request": approval_result,
        }

    @staticmethod
    async def execute_payment_reminder(contract_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a payment reminder to billing contacts for *contract_id*.
        """
        contract = await JobExecutor._load_contract(contract_id)
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not found"}

        current_state = getattr(contract, "workflow_state", "DRAFT")
        if current_state != "ACTIVE":
            return {
                "success": False,
                "error": f"Contract {contract_id} is not ACTIVE, skipping payment reminder",
            }

        await NotificationSystem.send_payment_reminder(contract)

        return {"success": True, "contract_id": contract_id}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_contract(contract_id: int) -> Optional[Any]:
        """
        Attempt to load a contract by uid.

        Tries the polymorphic BaseContract first; falls back to the legacy
        Contract document.  Returns None if nothing is found.
        """
        try:
            from backend.models.contracts.base_contract import BaseContract
            contract = await BaseContract.find_one(BaseContract.uid == contract_id)
            if contract is not None:
                return contract
        except Exception:  # noqa: BLE001
            pass

        try:
            from backend.models.projects import Contract
            contract = await Contract.find_one(Contract.uid == contract_id)
            return contract
        except Exception:  # noqa: BLE001
            return None
