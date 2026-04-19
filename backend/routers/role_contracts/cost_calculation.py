"""
Admin-only endpoint to trigger cost calculation for a submitted Daily Muster record.
Managers submit muster → Admin reviews → Admin triggers cost calculation.
Managers never see KWD rates or calculated costs.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/muster-cost",
    tags=["Muster Cost Calculation"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("MusterCostRouter", log_file="logs/muster_cost.log", level=logging.DEBUG)


def _require_admin(current_user: dict):
    """Raise 403 if user is not Admin or SuperAdmin."""
    role = current_user.get("role", "")
    if role not in ("Admin", "SuperAdmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or SuperAdmin can trigger cost calculation.",
        )


@router.post("/calculate/{fulfillment_id}", status_code=status.HTTP_200_OK)
async def calculate_muster_cost(
    fulfillment_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Admin triggers cost calculation for a specific Daily Muster record.

    Steps:
    1. Load the DailyRoleFulfillment document.
    2. Load the parent contract to get slot daily rates.
    3. Apply daily_rate to each filled slot → cost_applied.
    4. Set is_cost_calculated = True and record who calculated it.
    5. Save and return the updated summary.
    """
    _require_admin(current_user)

    from backend.models.role_contracts import DailyRoleFulfillment
    from backend.models.contracts import LabourContract

    fulfillment = await DailyRoleFulfillment.find_one(
        DailyRoleFulfillment.uid == fulfillment_id
    )
    if not fulfillment:
        raise HTTPException(status_code=404, detail=f"Muster record {fulfillment_id} not found.")

    if getattr(fulfillment, "is_cost_calculated", False):
        return {
            "message": "Cost already calculated for this record.",
            "fulfillment_id": fulfillment_id,
            "total_daily_cost": fulfillment.total_daily_cost,
            "already_calculated": True,
        }

    # Load contract to get slot rates
    contract = await LabourContract.find_one(
        LabourContract.uid == fulfillment.contract_id
    )
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract {fulfillment.contract_id} not found.")

    slot_rates = {slot.slot_id: slot.daily_rate for slot in (contract.role_slots or [])}

    # Apply rates to each slot record
    total_cost = 0.0
    shortage_cost = 0.0

    for record in fulfillment.role_fulfillments:
        rate = slot_rates.get(record.slot_id, record.daily_rate or 0.0)
        if record.attendance_status == "Half-Day":
            record.cost_applied = rate / 2
        elif record.is_filled and record.attendance_status == "Present":
            record.cost_applied = rate
        else:
            record.cost_applied = 0.0
            if not record.is_filled:
                shortage_cost += rate

        total_cost += record.cost_applied

    fulfillment.total_daily_cost   = total_cost
    fulfillment.shortage_cost_impact = shortage_cost
    fulfillment.total_roles_required = len(fulfillment.role_fulfillments)
    fulfillment.total_roles_filled   = sum(1 for r in fulfillment.role_fulfillments if r.is_filled)
    fulfillment.unfilled_slots       = [r.slot_id for r in fulfillment.role_fulfillments if not r.is_filled]

    # Mark as cost-calculated (admin-only fields)
    fulfillment.is_cost_calculated    = True  # type: ignore[attr-defined]
    fulfillment.cost_calculated_by    = current_user.get("uid")  # type: ignore[attr-defined]
    fulfillment.cost_calculated_at    = datetime.now()  # type: ignore[attr-defined]
    fulfillment.updated_at            = datetime.now()

    await fulfillment.save()

    logger.info(
        "Cost calculated for fulfillment %s by admin %s — total KWD %.3f",
        fulfillment_id,
        current_user.get("sub"),
        total_cost,
    )

    return {
        "message": "Cost calculated successfully.",
        "fulfillment_id": fulfillment_id,
        "date": fulfillment.date.date().isoformat() if fulfillment.date else None,
        "contract_id": fulfillment.contract_id,
        "total_slots": fulfillment.total_roles_required,
        "filled_slots": fulfillment.total_roles_filled,
        "total_daily_cost": round(total_cost, 3),
        "shortage_cost_impact": round(shortage_cost, 3),
        "unfilled_slots": fulfillment.unfilled_slots,
        "calculated_by": current_user.get("sub"),
    }


@router.post("/calculate-range", status_code=status.HTTP_200_OK)
async def calculate_cost_range(
    contract_id: int,
    month: int,
    year: int,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Admin calculates costs for ALL uncalculated muster records
    in a given contract for a given month.
    """
    _require_admin(current_user)

    from backend.models.role_contracts import DailyRoleFulfillment
    from backend.models.contracts import LabourContract
    from calendar import monthrange

    _, last_day = monthrange(year, month)
    start = datetime(year, month, 1)
    end   = datetime(year, month, last_day, 23, 59, 59)

    records = await DailyRoleFulfillment.find(
        DailyRoleFulfillment.contract_id == contract_id,
        DailyRoleFulfillment.date >= start,
        DailyRoleFulfillment.date <= end,
    ).to_list()

    contract = await LabourContract.find_one(LabourContract.uid == contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found.")

    slot_rates = {slot.slot_id: slot.daily_rate for slot in (contract.role_slots or [])}

    processed = 0
    skipped   = 0
    total_cost = 0.0

    for fulfillment in records:
        if getattr(fulfillment, "is_cost_calculated", False):
            skipped += 1
            continue

        day_cost = 0.0
        day_shortage = 0.0

        for record in fulfillment.role_fulfillments:
            rate = slot_rates.get(record.slot_id, record.daily_rate or 0.0)
            if record.attendance_status == "Half-Day":
                record.cost_applied = rate / 2
            elif record.is_filled and record.attendance_status == "Present":
                record.cost_applied = rate
            else:
                record.cost_applied = 0.0
                if not record.is_filled:
                    day_shortage += rate
            day_cost += record.cost_applied

        fulfillment.total_daily_cost     = day_cost
        fulfillment.shortage_cost_impact = day_shortage
        fulfillment.total_roles_filled   = sum(1 for r in fulfillment.role_fulfillments if r.is_filled)
        fulfillment.unfilled_slots       = [r.slot_id for r in fulfillment.role_fulfillments if not r.is_filled]
        fulfillment.is_cost_calculated   = True  # type: ignore[attr-defined]
        fulfillment.cost_calculated_by   = current_user.get("uid")  # type: ignore[attr-defined]
        fulfillment.cost_calculated_at   = datetime.now()  # type: ignore[attr-defined]
        fulfillment.updated_at           = datetime.now()

        await fulfillment.save()
        total_cost += day_cost
        processed  += 1

    logger.info(
        "Bulk cost calculation — contract %s, %s/%s — processed %d, skipped %d, total KWD %.3f",
        contract_id, month, year, processed, skipped, total_cost,
    )

    return {
        "message": f"Calculated costs for {processed} records. {skipped} already calculated.",
        "contract_id": contract_id,
        "month": month,
        "year": year,
        "records_processed": processed,
        "records_skipped": skipped,
        "total_monthly_cost": round(total_cost, 3),
    }
