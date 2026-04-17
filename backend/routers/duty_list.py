from fastapi import APIRouter, Depends, status
from typing import List
from backend import schemas
from backend.security import get_current_active_user
from backend.services import DutyListService

router = APIRouter(
    prefix="/duty_list",
    tags=["Duty List"],
    dependencies=[Depends(get_current_active_user)]
)

service = DutyListService()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_duty_assignment(assignments: List[schemas.DutyAssignmentCreate], current_user: dict = Depends(get_current_active_user)):
    """Assign employees to sites with managers."""
    return await service.create_duty_assignments(assignments, current_user)

@router.get("/{date}")
async def get_duty_list_by_date(date: str, current_user: dict = Depends(get_current_active_user)):
    """Get duty assignments for a specific date."""
    return await service.get_duty_list_by_date(date, current_user)

@router.delete("/{id}")
async def delete_duty_assignment(id: str):
    """Remove a duty assignment."""
    return await service.delete_duty_assignment(id)
