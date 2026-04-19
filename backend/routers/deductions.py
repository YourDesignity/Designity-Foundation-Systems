"""
Deductions CRUD router.
The Deduction model and schema existed but no router was ever written.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/deductions",
    tags=["Deductions"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("DeductionsRouter", log_file="logs/deductions_router.log", level=logging.DEBUG)


class DeductionCreate(BaseModel):
    employee_id: int
    pay_period: str      # YYYY-MM
    amount: float
    reason: Optional[str] = None


class DeductionResponse(BaseModel):
    id: str
    uid: Optional[int] = None
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    pay_period: str
    amount: float
    reason: Optional[str] = None


async def _enrich(record) -> dict:
    from backend.models.hr import Employee
    d = {
        "id": str(record.id),
        "uid": record.uid,
        "employee_id": record.employee_uid,
        "employee_name": None,
        "pay_period": record.pay_period,
        "amount": record.amount,
        "reason": getattr(record, "reason", None),
    }
    if record.employee_uid:
        emp = await Employee.find_one(Employee.uid == record.employee_uid)
        if emp:
            d["employee_name"] = emp.name
    return d


@router.get("/{year}/{month}", response_model=List[DeductionResponse])
async def get_deductions_by_month(
    year: int,
    month: int,
    current_user: dict = Depends(get_current_active_user),
):
    from backend.models.payroll import Deduction
    period = f"{year}-{month:02d}"
    records = await Deduction.find(Deduction.pay_period == period).to_list()
    return [await _enrich(r) for r in records]


@router.post("/", response_model=DeductionResponse, status_code=status.HTTP_201_CREATED)
async def create_deduction(
    payload: DeductionCreate,
    current_user: dict = Depends(get_current_active_user),
):
    from backend.models.payroll import Deduction
    from backend.database import get_next_uid
    new_uid = await get_next_uid("deductions")
    record = Deduction(
        uid=new_uid,
        employee_uid=payload.employee_id,
        pay_period=payload.pay_period,
        amount=payload.amount,
        reason=payload.reason,
    )
    await record.insert()
    logger.info("Deduction created uid=%d for employee %d", new_uid, payload.employee_id)
    return await _enrich(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deduction(
    record_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    from backend.models.payroll import Deduction
    from beanie import PydanticObjectId
    try:
        oid = PydanticObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid record ID.")
    record = await Deduction.get(oid)
    if not record:
        raise HTTPException(status_code=404, detail=f"Deduction {record_id} not found.")
    await record.delete()
    return None
