# backend/routers/contracts.py

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.models.contracts import LabourContract
from backend.models.workflow_history import WorkflowHistory
from backend.security import get_current_active_user
from backend.utils.audit import audit_create, audit_update, audit_delete, log_audit
from backend.utils.logger import setup_logger
from backend.workflows.engine import WorkflowEngine
from backend.workflows.states import ContractState

router = APIRouter(
    prefix="/api/contracts",
    tags=["Contracts API"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger(
    "ContractsAPIRouter",
    log_file="logs/contracts_api_router.log",
    level=logging.DEBUG,
)


# =============================================================================
# REQUEST / RESPONSE SCHEMAS
# =============================================================================


class ContractCreateRequest(BaseModel):
    contract_name: Optional[str] = None
    contract_type: str = "Labour"
    project_id: int
    project_name: Optional[str] = None
    client_name: Optional[str] = None
    start_date: datetime
    end_date: datetime
    contract_value: float = 0.0
    payment_terms: Optional[str] = None
    contract_terms: Optional[str] = None
    notes: Optional[str] = None
    enabled_modules: List[str] = []
    module_config: Dict[str, Any] = {}
    salary_strategy: str = "fixed"


class ContractUpdateRequest(BaseModel):
    contract_name: Optional[str] = None
    client_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    contract_value: Optional[float] = None
    payment_terms: Optional[str] = None
    contract_terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    enabled_modules: Optional[List[str]] = None
    module_config: Optional[Dict[str, Any]] = None
    salary_strategy: Optional[str] = None


class WorkflowTransitionRequest(BaseModel):
    target_state: str
    reason: Optional[str] = None


# =============================================================================
# HELPERS
# =============================================================================


async def _get_contract_or_404(contract_id: int) -> LabourContract:
    contract = await LabourContract.find_one(LabourContract.uid == contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    return contract


def _serialize_contract(contract: LabourContract) -> Dict[str, Any]:
    """Return a JSON-serialisable dict for a contract document."""
    data = contract.model_dump(mode="json")
    # Ensure the Beanie internal id is not exposed as ObjectId
    data.pop("id", None)
    data.pop("_id", None)
    data.pop("revision_id", None)
    return data


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/", response_model=Dict[str, Any])
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workflow_state: Optional[str] = Query(None),
    enabled_module: Optional[str] = Query(None, alias="module"),
    start_date_from: Optional[datetime] = Query(None),
    start_date_to: Optional[datetime] = Query(None),
    end_date_from: Optional[datetime] = Query(None),
    end_date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """List all contracts with pagination and optional filters."""
    query: Dict[str, Any] = {}

    if workflow_state:
        query["workflow_state"] = workflow_state
    if enabled_module:
        query["enabled_modules"] = enabled_module
    if start_date_from or start_date_to:
        sd: Dict[str, Any] = {}
        if start_date_from:
            sd["$gte"] = start_date_from
        if start_date_to:
            sd["$lte"] = start_date_to
        query["start_date"] = sd
    if end_date_from or end_date_to:
        ed: Dict[str, Any] = {}
        if end_date_from:
            ed["$gte"] = end_date_from
        if end_date_to:
            ed["$lte"] = end_date_to
        query["end_date"] = ed
    if search:
        query["$or"] = [
            {"contract_name": {"$regex": search, "$options": "i"}},
            {"contract_code": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
            {"project_name": {"$regex": search, "$options": "i"}},
        ]

    total = await LabourContract.find(query).count()
    skip = (page - 1) * page_size
    contracts = (
        await LabourContract.find(query)
        .sort(-LabourContract.created_at)
        .skip(skip)
        .limit(page_size)
        .to_list()
    )

    logger.info("Listed %d contracts (page %d)", len(contracts), page)
    return {
        "items": [_serialize_contract(c) for c in contracts],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_contract(
    body: ContractCreateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new contract."""
    from backend.database import get_next_uid

    uid = await get_next_uid("contracts")
    contract_code = f"CNT-{uid:04d}"

    contract = LabourContract(
        uid=uid,
        contract_code=contract_code,
        contract_name=body.contract_name or contract_code,
        contract_type=body.contract_type,
        project_id=body.project_id,
        project_name=body.project_name,
        client_name=body.client_name,
        start_date=body.start_date,
        end_date=body.end_date,
        contract_value=body.contract_value,
        payment_terms=body.payment_terms,
        contract_terms=body.contract_terms,
        notes=body.notes,
        enabled_modules=body.enabled_modules,
        module_config=body.module_config,
        salary_strategy=body.salary_strategy,
        workflow_state=ContractState.DRAFT,
        created_by_admin_id=current_user.get("uid"),
    )
    await contract.insert()

    # Audit log
    try:
        await audit_create(
            user=current_user,
            category="contracts",
            entity_type="contract",
            entity_id=str(uid),
            entity_name=contract_code,
            data={"contract_code": contract_code, "project_id": body.project_id},
        )
    except Exception:
        pass

    logger.info("Contract %s created by user %s", contract_code, current_user.get("uid"))
    return _serialize_contract(contract)


@router.get("/{contract_id}", response_model=Dict[str, Any])
async def get_contract(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get a single contract by its UID."""
    contract = await _get_contract_or_404(contract_id)
    return _serialize_contract(contract)


@router.put("/{contract_id}", response_model=Dict[str, Any])
async def update_contract(
    contract_id: int,
    body: ContractUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update a contract's editable fields."""
    contract = await _get_contract_or_404(contract_id)

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    contract.updated_at = datetime.now()
    await contract.save()

    # Audit log
    try:
        await audit_update(
            user=current_user,
            category="contracts",
            entity_type="contract",
            entity_id=str(contract_id),
            entity_name=contract.contract_code,
            after=update_data,
        )
    except Exception:
        pass

    logger.info("Contract %d updated by user %s", contract_id, current_user.get("uid"))
    return _serialize_contract(contract)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a contract. Only DRAFT or CANCELLED contracts may be deleted."""
    contract = await _get_contract_or_404(contract_id)

    if contract.workflow_state not in (ContractState.DRAFT, ContractState.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT or CANCELLED contracts can be deleted.",
        )

    await contract.delete()

    # Audit log
    try:
        await audit_delete(
            user=current_user,
            category="contracts",
            entity_type="contract",
            entity_id=str(contract_id),
            entity_name=contract.contract_code,
        )
    except Exception:
        pass

    logger.info("Contract %d deleted by user %s", contract_id, current_user.get("uid"))
    return None


# Mapping from action name to target ContractState
_ACTION_TO_STATE: Dict[str, str] = {
    "submit": ContractState.PENDING_APPROVAL,
    "approve": ContractState.ACTIVE,
    "reject": ContractState.DRAFT,
    "activate": ContractState.ACTIVE,
    "complete": ContractState.COMPLETED,
    "cancel": ContractState.CANCELLED,
    "suspend": ContractState.SUSPENDED,
}


@router.get("/{contract_id}/workflow/", response_model=Dict[str, Any])
async def get_workflow_state(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Return the current workflow state for a contract."""
    contract = await _get_contract_or_404(contract_id)
    return {
        "workflow_state": contract.workflow_state,
        "state_changed_at": (
            contract.updated_at.isoformat() if contract.updated_at else None
        ),
    }


@router.post("/{contract_id}/workflow/{action}", response_model=Dict[str, Any])
async def perform_workflow_action(
    contract_id: int,
    action: str,
    body: Optional[WorkflowTransitionRequest] = None,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Perform a named workflow action on a contract.

    Supported actions: submit, approve, reject, activate, complete, cancel, suspend.
    """
    target_state = _ACTION_TO_STATE.get(action)
    if target_state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action '{action}'. Valid actions: {list(_ACTION_TO_STATE.keys())}",
        )

    contract = await _get_contract_or_404(contract_id)
    reason = (body.reason if body else None) or action

    result = await WorkflowEngine.transition(
        contract=contract,
        target_state=target_state,
        changed_by=current_user.get("uid"),
        reason=reason,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Workflow transition failed"),
        )

    # Audit log
    try:
        await log_audit(
            user=current_user,
            action=f"contract_{action}",
            category="contracts",
            entity_type="contract",
            entity_id=str(contract_id),
            entity_name=contract.contract_code,
            description=(
                f"{current_user.get('name', 'Unknown')} performed '{action}' on "
                f"contract '{contract.contract_code}'"
            ),
            before_data={"workflow_state": result.get("from_state")},
            after_data={"workflow_state": result.get("to_state")},
        )
    except Exception:
        pass

    logger.info(
        "Contract %d: action '%s' by user %s → %s",
        contract_id,
        action,
        current_user.get("uid"),
        result.get("to_state"),
    )
    return {"contract": _serialize_contract(contract), "transition": result}


@router.patch("/{contract_id}/workflow", response_model=Dict[str, Any])
async def change_workflow_state(
    contract_id: int,
    body: WorkflowTransitionRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Transition a contract to a new workflow state."""
    contract = await _get_contract_or_404(contract_id)

    try:
        target = ContractState(body.target_state)
    except ValueError:
        valid = [s.value for s in ContractState]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target_state '{body.target_state}'. Valid values: {valid}",
        )

    result = await WorkflowEngine.transition(
        contract=contract,
        target_state=target,
        changed_by=current_user.get("uid"),
        reason=body.reason,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Workflow transition failed"),
        )

    # Audit log
    try:
        await log_audit(
            user=current_user,
            action="contract_workflow_transition",
            category="contracts",
            entity_type="contract",
            entity_id=str(contract_id),
            entity_name=contract.contract_code,
            description=(
                f"{current_user.get('name', 'Unknown')} transitioned contract "
                f"'{contract.contract_code}' from {result.get('from_state')} "
                f"to {result.get('to_state')}"
            ),
            before_data={"workflow_state": result.get("from_state")},
            after_data={"workflow_state": result.get("to_state"), "reason": body.reason},
        )
    except Exception:
        pass

    logger.info(
        "Contract %d transitioned %s → %s by user %s",
        contract_id,
        result.get("from_state"),
        result.get("to_state"),
        current_user.get("uid"),
    )
    return {"contract": _serialize_contract(contract), "transition": result}


@router.get("/{contract_id}/history", response_model=List[Dict[str, Any]])
async def get_contract_history(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Return the workflow transition history for a contract."""
    history = (
        await WorkflowHistory.find(WorkflowHistory.contract_id == contract_id)
        .sort(-WorkflowHistory.timestamp)
        .to_list()
    )

    return [
        {
            "from_state": h.from_state,
            "to_state": h.to_state,
            "changed_by": h.changed_by,
            "reason": h.reason,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            "metadata": h.metadata,
        }
        for h in history
    ]


@router.get("/{contract_id}/schedule/", response_model=List[Dict[str, Any]])
async def get_contract_scheduled_jobs(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Return scheduled automation jobs for a contract."""
    from backend.models.schedules import ScheduledJob

    jobs = (
        await ScheduledJob.find(
            ScheduledJob.target_type == "contract",
            ScheduledJob.target_id == contract_id,
        )
        .sort(-ScheduledJob.scheduled_for)
        .to_list()
    )

    return [
        {
            "uid": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "scheduled_for": job.scheduled_for.isoformat() if job.scheduled_for else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "retry_count": job.retry_count,
            "last_error": job.last_error,
            "payload": job.payload,
        }
        for job in jobs
    ]


@router.get("/{contract_id}/activity", response_model=List[Dict[str, Any]])
async def get_contract_activity(
    contract_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Return the combined activity log for a contract.

    Aggregates workflow history events and audit log entries for this contract
    so the frontend can display a unified timeline.
    """
    from backend.models.audit_log import AuditLog

    history = (
        await WorkflowHistory.find(WorkflowHistory.contract_id == contract_id)
        .sort(-WorkflowHistory.timestamp)
        .to_list()
    )

    audit_entries = (
        await AuditLog.find(
            AuditLog.entity_type == "contract",
            AuditLog.entity_id == str(contract_id),
        )
        .sort(-AuditLog.timestamp)
        .to_list()
    )

    activities: List[Dict[str, Any]] = []

    for h in history:
        activities.append(
            {
                "type": "workflow_transition",
                "user": h.changed_by,
                "message": f"State changed from {h.from_state} to {h.to_state}",
                "reason": h.reason,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            }
        )

    for entry in audit_entries:
        activities.append(
            {
                "type": entry.action,
                "user": entry.user_name,
                "message": entry.description,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            }
        )

    # Sort combined list by timestamp descending
    activities.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return activities
