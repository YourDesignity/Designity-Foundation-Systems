# backend/routers/substitutes.py

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.substitute_service import SubstituteService

router = APIRouter(
    prefix="/substitutes",
    tags=["Substitute Management"],
    dependencies=[Depends(get_current_active_user)]
)

service = SubstituteService()

# ===== SCHEMAS =====

class SubstituteAssignRequest(BaseModel):
    site_id: int
    start_date: date
    end_date: Optional[date] = None
    reason: str  # "sick_leave" | "vacation" | "shortage" | "emergency"
    replacing_employee_id: Optional[int] = None
    daily_rate: Optional[float] = None
    hourly_rate: Optional[float] = None

class SubstituteReleaseRequest(BaseModel):
    end_date: Optional[date] = None

class SubstituteUpdateRequest(BaseModel):
    substitute_rating: Optional[float] = None
    substitute_skills: Optional[List[str]] = None
    substitute_availability: Optional[str] = None
    can_be_substitute: Optional[bool] = None


# ===== ENDPOINTS =====

@router.get("/available")
async def get_available_substitutes(
    site_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all outsourced employees available to act as substitutes."""
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return await service.get_available_substitutes(site_id=site_id)


@router.get("/outsourced")
async def get_all_outsourced_employees(
    current_user: dict = Depends(get_current_active_user)
):
    """Get all outsourced/external employees."""
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return await service.get_all_outsourced_employees()


@router.post("/{employee_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_substitute(
    employee_id: int,
    request: SubstituteAssignRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign an outsourced employee as a substitute to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return await service.assign_substitute(
        employee_id=employee_id,
        site_id=request.site_id,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
        replacing_employee_id=request.replacing_employee_id,
        daily_rate=request.daily_rate,
        hourly_rate=request.hourly_rate,
        current_user=current_user,
    )


@router.delete("/{employee_id}/release", status_code=200)
async def release_substitute(
    employee_id: int,
    request: SubstituteReleaseRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Release a substitute employee from their current assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return await service.release_substitute(
        employee_id=employee_id,
        end_date=request.end_date,
    )


@router.patch("/{employee_id}/profile")
async def update_substitute_profile(
    employee_id: int,
    request: SubstituteUpdateRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Update substitute-specific fields for an outsourced employee."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update substitute profiles")

    return await service.update_substitute_profile(
        employee_id, request.model_dump(exclude_unset=True)
    )


@router.get("/site/{site_id}")
async def get_substitutes_at_site(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all active substitutes currently assigned to a site."""
    return await service.get_substitutes_at_site(site_id, current_user)
