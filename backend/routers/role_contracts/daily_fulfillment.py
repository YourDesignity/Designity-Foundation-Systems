"""Daily Role Fulfillment API routes for record, assignment, swap, and monthly reporting."""

from fastapi import APIRouter, Depends, status

from backend.schemas import (
    DailyFulfillmentCreate,
    RoleAssignmentRequest,
    SlotSwapRequest,
)
from backend.security import get_current_active_user
from backend.services.role_contracts_service import RoleContractsService

router = APIRouter(
    prefix="/daily-fulfillment",
    tags=["Daily Role Fulfillment"],
    dependencies=[Depends(get_current_active_user)],
)

service = RoleContractsService()


@router.post("/record", status_code=status.HTTP_201_CREATED)
async def record_daily_fulfillment(
    payload: DailyFulfillmentCreate,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.record_daily_fulfillment(payload, current_user)


@router.get("/unfilled")
async def get_unfilled_slots(
    current_user: dict = Depends(get_current_active_user),
):
    return await service.get_unfilled_slots()


@router.get("/{contract_id}/date/{date_str}")
async def get_daily_fulfillment(
    contract_id: int,
    date_str: str,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.get_daily_fulfillment(contract_id, date_str)


@router.put("/{fulfillment_id}/assign", status_code=status.HTTP_200_OK)
async def assign_employee_to_slot(
    fulfillment_id: int,
    payload: RoleAssignmentRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.assign_employee_to_slot(fulfillment_id, payload)


@router.put("/{fulfillment_id}/swap", status_code=status.HTTP_200_OK)
async def swap_employee_in_slot(
    fulfillment_id: int,
    payload: SlotSwapRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.swap_employee_in_slot(fulfillment_id, payload)


@router.get("/{contract_id}/month/{month}/year/{year}")
async def get_monthly_cost_report(
    contract_id: int,
    month: int,
    year: int,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.get_monthly_cost_report(contract_id, month, year)
