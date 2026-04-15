# backend/routers/substitutes.py

import logging
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import Employee, Site, Admin, SubstituteAssignment, TemporaryAssignment
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/substitutes",
    tags=["Substitute Management"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("SubstitutesRouter", log_file="logs/substitutes_router.log", level=logging.DEBUG)

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

    substitutes = await Employee.find(
        Employee.employee_type == "Outsourced",
        Employee.status == "Active",
        Employee.can_be_substitute == True,
        Employee.substitute_availability == "available"
    ).to_list()

    result = []
    for emp in substitutes:
        emp_dict = emp.model_dump(mode='json')
        result.append(emp_dict)

    logger.info(f"Retrieved {len(result)} available substitutes")
    return {
        "total": len(result),
        "substitutes": result
    }


@router.get("/outsourced")
async def get_all_outsourced_employees(
    current_user: dict = Depends(get_current_active_user)
):
    """Get all outsourced/external employees."""
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    employees = await Employee.find(
        Employee.employee_type == "Outsourced",
        Employee.status == "Active"
    ).to_list()

    return {
        "total": len(employees),
        "employees": [e.model_dump(mode='json') for e in employees]
    }


@router.post("/{employee_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_substitute(
    employee_id: int,
    request: SubstituteAssignRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign an outsourced employee as a substitute to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    employee = await Employee.find_one(Employee.uid == employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if employee.employee_type != "Outsourced":
        raise HTTPException(status_code=400, detail="Only Outsourced employees can be assigned as substitutes")

    if employee.current_substitute_assignment and employee.current_substitute_assignment.status == "Active":
        raise HTTPException(
            status_code=400,
            detail="Employee is already on an active substitute assignment"
        )

    site = await Site.find_one(Site.uid == request.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    manager_id = current_user.get("id")
    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if me:
            manager_id = me.uid

    replacing_name = None
    if request.replacing_employee_id:
        replacing_emp = await Employee.find_one(Employee.uid == request.replacing_employee_id)
        replacing_name = replacing_emp.name if replacing_emp else None

    assignment = SubstituteAssignment(
        site_id=request.site_id,
        site_name=site.name,
        start_date=datetime.combine(request.start_date, datetime.min.time()),
        end_date=datetime.combine(request.end_date, datetime.min.time()) if request.end_date else None,
        reason=request.reason,
        replacing_employee_id=request.replacing_employee_id,
        replacing_employee_name=replacing_name,
        assigned_by_manager_id=manager_id,
        daily_rate=request.daily_rate or employee.default_hourly_rate,
        hourly_rate=request.hourly_rate,
        status="Active"
    )

    employee.current_substitute_assignment = assignment
    employee.substitute_availability = "assigned"
    employee.can_be_substitute = True
    employee.substitute_assignment_history.append(assignment)
    employee.total_substitute_assignments += 1
    await employee.save()

    if employee.uid not in site.active_substitute_uids:
        site.active_substitute_uids.append(employee.uid)
        await site.save()

    # Also create a TemporaryAssignment record for tracking and payroll
    new_uid = await get_next_uid("temporary_assignments")
    temp_assignment = TemporaryAssignment(
        uid=new_uid,
        employee_id=employee_id,
        employee_name=employee.name,
        employee_type="Outsourced",
        employee_designation=employee.designation,
        assignment_type="Temporary",
        site_id=request.site_id,
        site_name=site.name,
        project_id=site.project_id or 0,
        manager_id=manager_id,
        replacing_employee_id=request.replacing_employee_id,
        replacing_employee_name=replacing_name,
        replacement_reason=request.reason,
        start_date=request.start_date,
        end_date=request.end_date or request.start_date,
        total_days=(request.end_date - request.start_date).days + 1 if request.end_date else 1,
        rate_type="Daily" if request.daily_rate else "Hourly",
        daily_rate=request.daily_rate or 0.0,
        hourly_rate=request.hourly_rate or 0.0,
        status="Active",
        created_by_admin_id=current_user.get("id")
    )
    await temp_assignment.insert()

    logger.info(f"Substitute {employee.name} assigned to site {site.name} for reason: {request.reason}")

    return {
        "message": "Substitute assigned successfully",
        "employee_id": employee_id,
        "employee_name": employee.name,
        "site_id": request.site_id,
        "site_name": site.name,
        "reason": request.reason,
        "temporary_assignment_id": temp_assignment.uid
    }


@router.delete("/{employee_id}/release", status_code=200)
async def release_substitute(
    employee_id: int,
    request: SubstituteReleaseRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Release a substitute employee from their current assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    employee = await Employee.find_one(Employee.uid == employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if not employee.current_substitute_assignment or employee.current_substitute_assignment.status != "Active":
        raise HTTPException(status_code=400, detail="Employee has no active substitute assignment")

    site_id = employee.current_substitute_assignment.site_id
    end = request.end_date or date.today()

    # Mark assignment as completed
    employee.current_substitute_assignment.status = "Completed"
    employee.current_substitute_assignment.end_date = datetime.combine(end, datetime.min.time())

    # Update history (last item)
    if employee.substitute_assignment_history:
        employee.substitute_assignment_history[-1].status = "Completed"
        employee.substitute_assignment_history[-1].end_date = datetime.combine(end, datetime.min.time())

    # Calculate days worked
    start = employee.current_substitute_assignment.start_date
    days = (end - start.date()).days + 1 if start else 1
    employee.total_days_as_substitute += max(1, days)

    employee.substitute_availability = "available"
    employee.current_substitute_assignment = None
    await employee.save()

    # Remove from site's active substitutes
    site = await Site.find_one(Site.uid == site_id)
    if site and employee_id in site.active_substitute_uids:
        site.active_substitute_uids.remove(employee_id)
        await site.save()

    # End the TemporaryAssignment record
    temp = await TemporaryAssignment.find_one(
        TemporaryAssignment.employee_id == employee_id,
        TemporaryAssignment.site_id == site_id,
        TemporaryAssignment.status == "Active"
    )
    if temp:
        temp.status = "Completed"
        temp.end_date = end
        await temp.save()

    logger.info(f"Substitute {employee.name} released from site {site_id}")

    return {
        "message": "Substitute released successfully",
        "employee_id": employee_id,
        "employee_name": employee.name,
        "days_worked": max(1, days),
    }


@router.patch("/{employee_id}/profile")
async def update_substitute_profile(
    employee_id: int,
    request: SubstituteUpdateRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Update substitute-specific fields for an outsourced employee."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update substitute profiles")

    employee = await Employee.find_one(Employee.uid == employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(employee, key, value)

    # If marking as substitute-capable, set availability if not already set
    if request.can_be_substitute and not employee.substitute_availability:
        employee.substitute_availability = "available"

    await employee.save()

    logger.info(f"Substitute profile updated successfully")
    return employee.model_dump(mode='json')


@router.get("/site/{site_id}")
async def get_substitutes_at_site(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all active substitutes currently assigned to a site."""
    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or site.assigned_manager_id != me.uid:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    substitutes = []
    for uid in site.active_substitute_uids:
        emp = await Employee.find_one(Employee.uid == uid)
        if emp:
            substitutes.append(emp.model_dump(mode='json'))

    return {
        "site_id": site_id,
        "site_name": site.name,
        "active_substitutes": len(substitutes),
        "substitutes": substitutes
    }
