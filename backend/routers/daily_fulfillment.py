# backend/routers/daily_fulfillment.py
"""
Daily Role Fulfillment API
--------------------------
Record which employees filled which contract role slots on a given work day.

Endpoints
---------
POST   /daily-fulfillment/record                              – Record daily fulfillment
GET    /daily-fulfillment/{contract_id}/date/{date}           – Get a specific day's record
PUT    /daily-fulfillment/{fulfillment_id}/assign             – Assign employee to a slot
PUT    /daily-fulfillment/{fulfillment_id}/swap               – Swap employee in a slot
GET    /daily-fulfillment/{contract_id}/month/{month}/year/{year} – Monthly cost report
GET    /daily-fulfillment/unfilled                            – All unfilled slots (alerts)
"""

import logging
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models import Contract, DailyRoleFulfillment, Employee, RoleFulfillmentRecord
from backend.database import get_next_uid
from backend.schemas import (
    DailyFulfillmentCreate,
    DailyFulfillmentUpdate,
    RoleAssignmentRequest,
    SlotSwapRequest,
    MonthlyRoleCostReport,
)
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger
from backend.models import _coerce_date_to_datetime

router = APIRouter(
    prefix="/daily-fulfillment",
    tags=["Daily Role Fulfillment"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("DailyFulfillmentRouter", log_file="logs/daily_fulfillment.log", level=logging.DEBUG)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_date_param(date_str: str) -> datetime:
    """Parse a YYYY-MM-DD string into a midnight datetime, raising 400 on bad format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format '{date_str}'. Use YYYY-MM-DD.")


def _build_summary(fulfillment: DailyRoleFulfillment) -> None:
    """Recalculate summary fields from role_fulfillments list (in-place)."""
    fulfillment.total_roles_required = len(fulfillment.role_fulfillments)
    fulfillment.total_roles_filled = sum(1 for r in fulfillment.role_fulfillments if r.is_filled)
    fulfillment.total_daily_cost = sum(r.cost_applied for r in fulfillment.role_fulfillments)
    fulfillment.unfilled_slots = [r.slot_id for r in fulfillment.role_fulfillments if not r.is_filled]
    contract_slot_rate = {r.slot_id: r.daily_rate for r in fulfillment.role_fulfillments}
    fulfillment.shortage_cost_impact = sum(
        contract_slot_rate.get(s, 0.0) for s in fulfillment.unfilled_slots
    )


async def _validate_no_double_booking(
    employee_id: int,
    work_date: datetime,
    exclude_fulfillment_id: Optional[int] = None,
) -> None:
    """Raise 409 if employee is already assigned to another slot on the same day."""
    query = DailyRoleFulfillment.find(DailyRoleFulfillment.date == work_date)
    records = await query.to_list()
    for rec in records:
        if exclude_fulfillment_id and rec.uid == exclude_fulfillment_id:
            continue
        for rf in rec.role_fulfillments:
            if rf.employee_id == employee_id and rf.is_filled:
                raise HTTPException(
                    status_code=409,
                    detail=f"Employee {employee_id} is already assigned to slot '{rf.slot_id}' on this day",
                )


# ---------------------------------------------------------------------------
# POST /daily-fulfillment/record
# ---------------------------------------------------------------------------

@router.post("/record", status_code=status.HTTP_201_CREATED)
async def record_daily_fulfillment(
    payload: DailyFulfillmentCreate,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Record which employees filled role slots on a specific day.

    Validation rules:
    * The date cannot be in the future.
    * Manager can only record for sites they are assigned to (unless Admin/SuperAdmin).
    * Employee designation must match slot designation.
    * Cannot double-book (same employee, same day, different slots).
    * No duplicate record for (contract_id, date).
    """
    # Date must not be in the future
    work_date = _coerce_date_to_datetime(payload.date)
    today_midnight = datetime.combine(date.today(), datetime.min.time())
    if work_date > today_midnight:
        raise HTTPException(status_code=400, detail="Cannot record fulfillment for a future date")

    # Permission: Site Managers can only record for their assigned sites
    role = current_user.get("role")
    if role == "Site Manager":
        assigned_sites: List[int] = current_user.get("sites") or []
        if payload.site_id not in assigned_sites:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this site",
            )

    # Ensure contract exists
    contract = await Contract.find_one(Contract.uid == payload.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # No duplicate per (contract_id, date)
    existing = await DailyRoleFulfillment.find_one(
        DailyRoleFulfillment.contract_id == payload.contract_id,
        DailyRoleFulfillment.date == work_date,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Fulfillment record already exists for contract {payload.contract_id} on this date "
                f"(uid={existing.uid}). Use PUT /{existing.uid}/assign or PUT /{existing.uid}/swap to update individual slots."
            ),
        )

    # Build a lookup of contract slot designations
    slot_designation: dict[str, str] = {s.slot_id: s.designation for s in contract.role_slots}

    # Validate & collect employee IDs that are filled today (for double-booking check)
    filled_employees: dict[int, str] = {}  # employee_id → slot_id

    records: List[RoleFulfillmentRecord] = []
    for rf_data in payload.role_fulfillments:
        # Designation check
        expected_designation = slot_designation.get(rf_data.slot_id)
        if expected_designation and rf_data.designation != expected_designation:
            raise HTTPException(
                status_code=400,
                detail=f"Slot '{rf_data.slot_id}' requires designation '{expected_designation}', got '{rf_data.designation}'",
            )

        # Double-booking check within this submission
        if rf_data.is_filled and rf_data.employee_id is not None:
            if rf_data.employee_id in filled_employees:
                raise HTTPException(
                    status_code=409,
                    detail=f"Employee {rf_data.employee_id} cannot be assigned to both slot '{filled_employees[rf_data.employee_id]}' and '{rf_data.slot_id}' on the same day",
                )
            filled_employees[rf_data.employee_id] = rf_data.slot_id

        cost_applied = rf_data.daily_rate if rf_data.is_filled else 0.0

        records.append(
            RoleFulfillmentRecord(
                slot_id=rf_data.slot_id,
                designation=rf_data.designation,
                daily_rate=rf_data.daily_rate,
                employee_id=rf_data.employee_id,
                employee_name=rf_data.employee_name,
                is_filled=rf_data.is_filled,
                attendance_status=rf_data.attendance_status,
                replacement_employee_id=rf_data.replacement_employee_id,
                replacement_employee_name=rf_data.replacement_employee_name,
                replacement_reason=rf_data.replacement_reason,
                cost_applied=cost_applied,
                payment_status=rf_data.payment_status,
                notes=rf_data.notes,
            )
        )

    # Cross-day double-booking check against existing records in the DB
    for emp_id in filled_employees:
        await _validate_no_double_booking(emp_id, work_date)

    new_uid = await get_next_uid("daily_role_fulfillments")
    fulfillment = DailyRoleFulfillment(
        uid=new_uid,
        contract_id=payload.contract_id,
        site_id=payload.site_id,
        date=work_date,
        role_fulfillments=records,
        recorded_by_manager_id=payload.recorded_by_manager_id,
    )
    _build_summary(fulfillment)
    await fulfillment.insert()

    logger.info(
        f"Daily fulfillment recorded: contract={payload.contract_id} date={work_date.date()} uid={new_uid}"
    )
    return fulfillment.model_dump(mode="json")


# ---------------------------------------------------------------------------
# GET /daily-fulfillment/unfilled  (must be before /{contract_id}/…)
# ---------------------------------------------------------------------------

@router.get("/unfilled")
async def get_unfilled_slots(
    current_user: dict = Depends(get_current_active_user),
):
    """Return all fulfillment records that have at least one unfilled slot (alert system)."""
    records = await DailyRoleFulfillment.find(
        DailyRoleFulfillment.total_roles_filled < DailyRoleFulfillment.total_roles_required
    ).sort("-date").to_list()

    return [r.model_dump(mode="json") for r in records]


# ---------------------------------------------------------------------------
# GET /daily-fulfillment/{contract_id}/date/{date}
# ---------------------------------------------------------------------------

@router.get("/{contract_id}/date/{date_str}")
async def get_daily_fulfillment(
    contract_id: int,
    date_str: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Get the fulfillment record for a specific contract and date (YYYY-MM-DD)."""
    work_date = _parse_date_param(date_str)
    record = await DailyRoleFulfillment.find_one(
        DailyRoleFulfillment.contract_id == contract_id,
        DailyRoleFulfillment.date == work_date,
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No fulfillment record found for contract {contract_id} on {date_str}",
        )
    return record.model_dump(mode="json")


# ---------------------------------------------------------------------------
# PUT /daily-fulfillment/{fulfillment_id}/assign
# ---------------------------------------------------------------------------

@router.put("/{fulfillment_id}/assign", status_code=status.HTTP_200_OK)
async def assign_employee_to_slot(
    fulfillment_id: int,
    payload: RoleAssignmentRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Assign an employee to a specific slot in an existing fulfillment record.
    Validates designation match and prevents double-booking.
    """
    fulfillment = await DailyRoleFulfillment.find_one(DailyRoleFulfillment.uid == fulfillment_id)
    if not fulfillment:
        raise HTTPException(status_code=404, detail="Fulfillment record not found")

    # Validate slot exists in fulfillment
    slot_record = next((r for r in fulfillment.role_fulfillments if r.slot_id == payload.slot_id), None)
    if not slot_record:
        raise HTTPException(status_code=404, detail=f"Slot '{payload.slot_id}' not found in this record")

    # Double-booking check
    await _validate_no_double_booking(payload.employee_id, fulfillment.date, exclude_fulfillment_id=fulfillment_id)

    # Validate employee designation against contract slot
    contract = await Contract.find_one(Contract.uid == fulfillment.contract_id)
    if contract:
        slot_def = next((s for s in contract.role_slots if s.slot_id == payload.slot_id), None)
        if slot_def:
            employee = await Employee.find_one(Employee.uid == payload.employee_id)
            if employee and employee.designation != slot_def.designation:
                raise HTTPException(
                    status_code=400,
                    detail=f"Employee designation '{employee.designation}' does not match slot designation '{slot_def.designation}'",
                )

    slot_record.employee_id = payload.employee_id
    slot_record.employee_name = payload.employee_name
    slot_record.is_filled = True
    slot_record.attendance_status = payload.attendance_status
    slot_record.cost_applied = slot_record.daily_rate
    if payload.notes:
        slot_record.notes = payload.notes

    _build_summary(fulfillment)
    fulfillment.updated_at = datetime.now()
    await fulfillment.save()

    logger.info("Assigned employee to slot '%s' in fulfillment %d", payload.slot_id, fulfillment_id)
    return fulfillment.model_dump(mode="json")


# ---------------------------------------------------------------------------
# PUT /daily-fulfillment/{fulfillment_id}/swap
# ---------------------------------------------------------------------------

@router.put("/{fulfillment_id}/swap", status_code=status.HTTP_200_OK)
async def swap_employee_in_slot(
    fulfillment_id: int,
    payload: SlotSwapRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Swap the employee filling a slot (same designation required).
    The previous employee is moved to replacement fields for audit trail.
    """
    fulfillment = await DailyRoleFulfillment.find_one(DailyRoleFulfillment.uid == fulfillment_id)
    if not fulfillment:
        raise HTTPException(status_code=404, detail="Fulfillment record not found")

    slot_record = next((r for r in fulfillment.role_fulfillments if r.slot_id == payload.slot_id), None)
    if not slot_record:
        raise HTTPException(status_code=404, detail=f"Slot '{payload.slot_id}' not found in this record")

    # Validate designation of new employee
    contract = await Contract.find_one(Contract.uid == fulfillment.contract_id)
    if contract:
        slot_def = next((s for s in contract.role_slots if s.slot_id == payload.slot_id), None)
        if slot_def:
            new_employee = await Employee.find_one(Employee.uid == payload.new_employee_id)
            if new_employee and new_employee.designation != slot_def.designation:
                raise HTTPException(
                    status_code=400,
                    detail=f"New employee designation '{new_employee.designation}' does not match slot designation '{slot_def.designation}'",
                )

    # Double-booking check for new employee
    await _validate_no_double_booking(payload.new_employee_id, fulfillment.date, exclude_fulfillment_id=fulfillment_id)

    # Keep audit trail
    slot_record.replacement_employee_id = slot_record.employee_id
    slot_record.replacement_employee_name = slot_record.employee_name
    slot_record.replacement_reason = payload.reason

    # Set new employee
    slot_record.employee_id = payload.new_employee_id
    slot_record.employee_name = payload.new_employee_name
    slot_record.is_filled = True
    slot_record.attendance_status = "Present"
    slot_record.cost_applied = slot_record.daily_rate

    _build_summary(fulfillment)
    fulfillment.updated_at = datetime.now()
    await fulfillment.save()

    logger.info("Swapped employee in slot '%s' for fulfillment %d", payload.slot_id, fulfillment_id)
    return fulfillment.model_dump(mode="json")


# ---------------------------------------------------------------------------
# GET /daily-fulfillment/{contract_id}/month/{month}/year/{year}
# ---------------------------------------------------------------------------

@router.get("/{contract_id}/month/{month}/year/{year}")
async def get_monthly_cost_report(
    contract_id: int,
    month: int,
    year: int,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Return a monthly cost aggregation report for a Labour contract.

    Returns totals and a per-day breakdown of role fulfillment and costs.
    """
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    current_year = datetime.now().year
    if year < current_year - 10 or year > current_year + 10:
        raise HTTPException(status_code=400, detail="Year is outside the valid range (±10 years from current year)")

    # Date range for the month
    start_dt = datetime(year, month, 1)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1)
    else:
        end_dt = datetime(year, month + 1, 1)

    records = await DailyRoleFulfillment.find(
        DailyRoleFulfillment.contract_id == contract_id,
        DailyRoleFulfillment.date >= start_dt,
        DailyRoleFulfillment.date < end_dt,
    ).sort("+date").to_list()

    if not records:
        return MonthlyRoleCostReport(
            contract_id=contract_id,
            month=month,
            year=year,
            total_days_recorded=0,
            total_roles_required=0,
            total_roles_filled=0,
            total_cost=0.0,
            shortage_cost_impact=0.0,
            fulfillment_rate=0.0,
            cost_by_designation={},
            daily_breakdown=[],
        )

    total_required = sum(r.total_roles_required for r in records)
    total_filled = sum(r.total_roles_filled for r in records)
    total_cost = sum(r.total_daily_cost for r in records)
    total_shortage = sum(r.shortage_cost_impact for r in records)
    fulfillment_rate = (total_filled / total_required) if total_required > 0 else 0.0

    # Aggregate cost by designation
    cost_by_designation: dict = {}
    for rec in records:
        for rf in rec.role_fulfillments:
            if rf.is_filled:
                cost_by_designation[rf.designation] = (
                    cost_by_designation.get(rf.designation, 0.0) + rf.cost_applied
                )

    daily_breakdown = [
        {
            "date": r.date.date().isoformat(),
            "total_required": r.total_roles_required,
            "total_filled": r.total_roles_filled,
            "total_cost": r.total_daily_cost,
            "shortage_cost_impact": r.shortage_cost_impact,
            "unfilled_slots": r.unfilled_slots,
        }
        for r in records
    ]

    return MonthlyRoleCostReport(
        contract_id=contract_id,
        month=month,
        year=year,
        total_days_recorded=len(records),
        total_roles_required=total_required,
        total_roles_filled=total_filled,
        total_cost=total_cost,
        shortage_cost_impact=total_shortage,
        fulfillment_rate=round(fulfillment_rate, 4),
        cost_by_designation=cost_by_designation,
        daily_breakdown=daily_breakdown,
    )
