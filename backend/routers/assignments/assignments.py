# backend/routers/assignments.py

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.assignments.assignment_service import AssignmentService

router = APIRouter(
    prefix="/assignments",
    tags=["Employee Assignments"],
    dependencies=[Depends(get_current_active_user)]
)

service = AssignmentService()

# ===== SCHEMAS =====

class BulkAssignmentCreate(BaseModel):
    site_id: int
    employee_ids: List[int]
    assignment_start: date
    assignment_end: Optional[date] = None

class SingleAssignmentCreate(BaseModel):
    employee_id: int
    site_id: int
    assignment_start: date
    assignment_end: Optional[date] = None

class AssignmentUpdate(BaseModel):
    assignment_start: Optional[date] = None
    assignment_end: Optional[date] = None
    status: Optional[str] = None

# ===== ENDPOINTS =====

@router.post("/assign-employees", status_code=status.HTTP_201_CREATED)
async def bulk_assign_employees(
    assignment_data: BulkAssignmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk assign multiple employees to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign employees")

    return await service.bulk_assign_employees(
        site_id=assignment_data.site_id,
        employee_ids=assignment_data.employee_ids,
        assignment_start=assignment_data.assignment_start,
        assignment_end=assignment_data.assignment_end,
        created_by_admin_id=current_user.get("id"),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def assign_single_employee(
    assignment_data: SingleAssignmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign a single employee to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign employees")

    result = await service.bulk_assign_employees(
        site_id=assignment_data.site_id,
        employee_ids=[assignment_data.employee_id],
        assignment_start=assignment_data.assignment_start,
        assignment_end=assignment_data.assignment_end,
        created_by_admin_id=current_user.get("id"),
    )

    if result["created_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail=result["failures"][0]["reason"] if result["failures"] else "Failed to assign employee"
        )

    return result["assignments"][0]


@router.get("/available/employees")
async def get_available_employees(
    current_user: dict = Depends(get_current_active_user)
):
    """Get list of employees available for assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view available employees")

    return await service.get_available_employees()


@router.get("/employee/{employee_id}/history")
async def get_employee_assignment_history(
    employee_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get assignment history for an employee."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignment history")

    return await service.get_employee_history(employee_id)


@router.get("/site/{site_id}/employees")
async def get_site_assignments(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all employees assigned to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view site assignments")

    return await service.get_site_employees(site_id)


@router.get("/")
async def get_all_assignments(
    site_id: Optional[int] = None,
    project_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all assignments with optional filters."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignments")

    return await service.list_assignments(
        site_id=site_id, project_id=project_id,
        employee_id=employee_id, status=status,
    )


@router.get("/{assignment_id}")
async def get_assignment_details(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get details of a specific assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignment details")

    return await service.get_assignment_details(assignment_id)


@router.put("/{assignment_id}")
async def update_assignment(
    assignment_id: int,
    assignment_update: AssignmentUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update assignment details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update assignments")

    return await service.update_assignment_fields(
        assignment_id, assignment_update.model_dump(exclude_unset=True)
    )


@router.delete("/{assignment_id}", status_code=204)
async def unassign_employee(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Unassign an employee from a site (end the assignment)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can unassign employees")

    await service.unassign_employee(assignment_id)
    return None
