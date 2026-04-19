"""
Overtime CRUD router.
The Overtime model and schema existed but the router was never created,
causing all /overtime/* requests to return 404.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/overtime",
    tags=["Overtime"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("OvertimeRouter", log_file="logs/overtime_router.log", level=logging.DEBUG)


# ─── Request / Response schemas ───────────────────────────────────────────────

class OvertimeCreate(BaseModel):
    employee_id: int
    date: str           # YYYY-MM-DD
    hours: float
    type: str = "Normal"   # Normal | Offday
    reason: Optional[str] = None


class OvertimeResponse(BaseModel):
    id: str             # MongoDB _id as string (frontend uses rec.id)
    uid: Optional[int] = None
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    date: str
    hours: float
    type: str
    reason: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _enrich_with_employee_name(record) -> dict:
    """Add employee_name to a record dict for display."""
    from backend.models.hr import Employee
    d = {
        "id": str(record.id),
        "uid": record.uid,
        "employee_id": record.employee_uid,
        "employee_name": None,
        "date": record.date,
        "hours": record.hours,
        "type": record.type,
        "reason": getattr(record, "reason", None),
    }
    if record.employee_uid:
        emp = await Employee.find_one(Employee.uid == record.employee_uid)
        if emp:
            d["employee_name"] = emp.name
    return d


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{year}/{month}", response_model=List[OvertimeResponse])
async def get_overtime_by_month(
    year: int,
    month: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Fetch all overtime records for a given year/month."""
    from backend.models.payroll import Overtime

    # Filter by date prefix YYYY-MM
    month_prefix = f"{year}-{str(month).padStart(2, '0')}" if False else f"{year}-{month:02d}"

    all_records = await Overtime.find_all().to_list()
    monthly = [r for r in all_records if r.date.startswith(month_prefix)]

    result = []
    for record in monthly:
        result.append(await _enrich_with_employee_name(record))

    logger.debug("Overtime GET %d/%d — %d records", year, month, len(result))
    return result


@router.post("/", response_model=OvertimeResponse, status_code=status.HTTP_201_CREATED)
async def create_overtime(
    payload: OvertimeCreate,
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new overtime record."""
    from backend.models.payroll import Overtime
    from backend.database import get_next_uid

    new_uid = await get_next_uid("overtime")
    record = Overtime(
        uid=new_uid,
        employee_uid=payload.employee_id,
        date=payload.date,
        hours=payload.hours,
        type=payload.type,
        reason=payload.reason,
    )
    await record.insert()
    logger.info("Overtime created uid=%d for employee %d", new_uid, payload.employee_id)
    return await _enrich_with_employee_name(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_overtime(
    record_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Delete an overtime record by its MongoDB _id string."""
    from backend.models.payroll import Overtime
    from beanie import PydanticObjectId

    try:
        oid = PydanticObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid record ID format.")

    record = await Overtime.get(oid)
    if not record:
        raise HTTPException(status_code=404, detail=f"Overtime record {record_id} not found.")

    await record.delete()
    logger.info("Overtime deleted id=%s", record_id)
    return None
