# backend/routers/schedules.py

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from backend.schemas import ScheduleCreate
from backend.security import get_current_active_user, require_permission
from backend.services.hr.schedule_service import ScheduleService
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/schedules",
    tags=["Schedule Management"],
    dependencies=[Depends(get_current_active_user)]
)

# --- Initialize Logger ---
logger = setup_logger("SchedulesRouter", log_file="logs/schedules_router.log", level=logging.DEBUG)
service = ScheduleService()

# =============================================================================
# 1. BULK CREATE SCHEDULES
# =============================================================================

@router.post("/bulk", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("schedule:edit"))])
async def create_bulk_schedules(schedule_data: ScheduleCreate):
    """
    Creates schedule records for multiple employees over a date range.
    Handles duplicates gracefully.
    """
    logger.info(f"ENDPOINT START: POST /schedules/bulk")
    return await service.create_bulk_schedules(schedule_data)

# =============================================================================
# 2. READ SCHEDULES (With Filtering)
# =============================================================================

@router.get("/", response_model=List[dict])
async def get_schedules(
    start_date: str,
    end_date: str,
    site_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Retrieves schedules based on permissions.
    """
    logger.info(f"ENDPOINT START: GET /schedules. Range: {start_date} to {end_date}")
    return await service.get_schedules_for_user(
        start_date=start_date,
        end_date=end_date,
        current_user=current_user,
        site_id=site_id,
        employee_id=employee_id,
    )
