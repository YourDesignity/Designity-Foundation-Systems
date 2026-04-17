# backend/routers/temporary_assignments.py

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.assignments.temporary_assignment_service import TemporaryAssignmentService

router = APIRouter(
    prefix="/temp-assignments",
    tags=["Temporary Assignments"],
    dependencies=[Depends(get_current_active_user)]
)

service = TemporaryAssignmentService()

# ===== SCHEMAS =====

class TempWorkerAssignmentItem(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    rate_type: Optional[str] = "Daily"   # Daily | Hourly
    daily_rate: Optional[float] = None
    hourly_rate: Optional[float] = None
    total_hours: Optional[float] = None

class BulkTempAssignmentCreate(BaseModel):
    site_id: int
    workers: List[TempWorkerAssignmentItem]
    replacement_reason: Optional[str] = None
    replacing_employee_id: Optional[int] = None
    replacing_employee_name: Optional[str] = None

class SingleTempAssignmentCreate(BaseModel):
    employee_id: int
    site_id: int
    start_date: date
    end_date: date
    rate_type: Optional[str] = "Daily"
    daily_rate: Optional[float] = None
    hourly_rate: Optional[float] = None
    total_hours: Optional[float] = None
    replacement_reason: Optional[str] = None
    replacing_employee_id: Optional[int] = None
    replacing_employee_name: Optional[str] = None

class TempAssignmentUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rate_type: Optional[str] = None
    daily_rate: Optional[float] = None
    hourly_rate: Optional[float] = None
    total_hours: Optional[float] = None
    status: Optional[str] = None

class RegisterTempWorkerCreate(BaseModel):
    name: str
    phone_kuwait: Optional[str] = None
    designation: str
    agency_name: Optional[str] = None
    rate_type: Optional[str] = "Daily"
    daily_rate: Optional[float] = 0.0
    hourly_rate: Optional[float] = 0.0
    employee_code: Optional[str] = None


# ===== ENDPOINTS =====

# --- IMPORTANT: Fixed paths must come before parameterized paths ---

@router.get("/available")
async def get_available_temp_workers(
    current_user: dict = Depends(get_current_active_user)
):
    """Get list of available temporary/outsourced workers not currently assigned."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view available workers")

    return await service.get_available_temp_workers()


@router.get("/workers")
async def get_all_temp_workers(
    available_only: Optional[bool] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all temporary/outsourced workers, optionally filtered by availability."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view workers")

    return await service.get_all_temp_workers(available_only=available_only)


@router.get("/cost-summary")
async def get_cost_summary(
    site_id: Optional[int] = None,
    project_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get cost analysis comparing company vs external labor costs."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view cost summaries")

    return await service.get_cost_summary(
        site_id=site_id, project_id=project_id,
        month=month, year=year,
    )


@router.post("/register-worker", status_code=status.HTTP_201_CREATED)
async def register_temp_worker(
    worker_data: RegisterTempWorkerCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Register a new temporary/outsourced worker."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can register workers")

    return await service.register_temp_worker(
        name=worker_data.name,
        designation=worker_data.designation,
        phone_kuwait=worker_data.phone_kuwait,
        agency_name=worker_data.agency_name,
        rate_type=worker_data.rate_type,
        daily_rate=worker_data.daily_rate,
        hourly_rate=worker_data.hourly_rate,
        employee_code=worker_data.employee_code,
    )


@router.post("/assign-workers", status_code=status.HTTP_201_CREATED)
async def bulk_assign_temp_workers(
    assignment_data: BulkTempAssignmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk assign multiple temp workers to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign workers")

    workers = [w.model_dump() for w in assignment_data.workers]

    return await service.bulk_assign_temp_workers(
        site_id=assignment_data.site_id,
        workers=workers,
        replacement_reason=assignment_data.replacement_reason,
        replacing_employee_id=assignment_data.replacing_employee_id,
        replacing_employee_name=assignment_data.replacing_employee_name,
        created_by_admin_id=current_user.get("id"),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def assign_single_temp_worker(
    assignment_data: SingleTempAssignmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign a single temporary worker to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign workers")

    workers = [
        {
            "employee_id": assignment_data.employee_id,
            "start_date": assignment_data.start_date,
            "end_date": assignment_data.end_date,
            "rate_type": assignment_data.rate_type,
            "daily_rate": assignment_data.daily_rate,
            "hourly_rate": assignment_data.hourly_rate,
            "total_hours": assignment_data.total_hours,
        }
    ]

    result = await service.bulk_assign_temp_workers(
        site_id=assignment_data.site_id,
        workers=workers,
        replacement_reason=assignment_data.replacement_reason,
        replacing_employee_id=assignment_data.replacing_employee_id,
        replacing_employee_name=assignment_data.replacing_employee_name,
        created_by_admin_id=current_user.get("id"),
    )

    if result["created_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail=result["failures"][0]["reason"] if result["failures"] else "Failed to assign worker"
        )

    return result["assignments"][0]


@router.get("/site/{site_id}")
async def get_temp_workers_at_site(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all temporary workers at a specific site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view site workers")

    return await service.get_temp_workers_at_site(site_id)


@router.get("/worker/{worker_id}/history")
async def get_worker_assignment_history(
    worker_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get assignment history for a temporary worker."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view worker history")

    return await service.get_worker_history(worker_id)


@router.get("/")
async def get_all_temp_assignments(
    site_id: Optional[int] = None,
    status: Optional[str] = None,
    start_after: Optional[date] = None,
    end_before: Optional[date] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all temporary assignments with optional filters."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignments")

    return await service.list_temp_assignments(
        site_id=site_id, status=status,
        start_after=start_after, end_before=end_before,
    )


@router.get("/{assignment_id}")
async def get_temp_assignment_details(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get details of a specific temporary assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignment details")

    return await service.get_temp_assignment_details(assignment_id)


@router.put("/{assignment_id}")
async def update_temp_assignment(
    assignment_id: int,
    update_data: TempAssignmentUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update a temporary assignment (dates, rates, status)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update assignments")

    return await service.update_temp_assignment_fields(
        assignment_id, update_data.model_dump(exclude_unset=True)
    )


@router.delete("/{assignment_id}", status_code=200)
async def end_temp_assignment(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """End a temporary assignment (set status to Completed)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can end assignments")

    return await service.end_temp_assignment_for_router(assignment_id)
