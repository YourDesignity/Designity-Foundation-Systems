import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend import schemas
from backend.security import get_current_active_user
from backend.services.duty_list_service import DutyListService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/duty_list",
    tags=["Duty List"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("DutyListRouter", log_file="logs/duty_list.log", level=logging.DEBUG)
service = DutyListService()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_duty_assignment(assignments: List[schemas.DutyAssignmentCreate], current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Only Admins and Site Managers can assign workforce duties.")

    try:
        return await service.create_duty_assignments(assignments)
    except Exception as e:
        logger.error(f"POST Duty Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save assignments.")

@router.get("/{date}")
async def get_duty_list_by_date(date: str, current_user: dict = Depends(get_current_active_user)):
    try:
        return await service.get_duty_list_by_date(date, current_user)
    except Exception as e:
        logger.error(f"GET Duty Error: {e}")
        return []

@router.delete("/{id}")
async def delete_duty_assignment(id: str):
    try:
        return await service.delete_duty_assignment(id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Delete failed")