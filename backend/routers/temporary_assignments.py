# backend/routers/temporary_assignments.py

import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import (
    TemporaryAssignment, Employee, Site, Project,
    Contract, Admin
)
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/temp-assignments",
    tags=["Temporary Assignments"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("TempAssignmentsRouter", log_file="logs/temp_assignments_router.log", level=logging.DEBUG)

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


# ===== HELPER FUNCTIONS =====

def calculate_cost(rate_type: str, daily_rate: float, hourly_rate: float,
                   start_date: date, end_date: date, total_hours: Optional[float] = None) -> float:
    """Calculate cost based on rate type and dates."""
    if rate_type == "Daily":
        days = (end_date - start_date).days + 1
        return days * daily_rate
    elif rate_type == "Hourly":
        hours = total_hours if total_hours else 8.0 * ((end_date - start_date).days + 1)
        return hours * hourly_rate
    return 0.0


# ===== ENDPOINTS =====

# --- IMPORTANT: Fixed paths must come before parameterized paths ---

@router.get("/available")
async def get_available_temp_workers(
    current_user: dict = Depends(get_current_active_user)
):
    """Get list of available temporary/outsourced workers not currently assigned."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view available workers")

    available_workers = await Employee.find(
        Employee.employee_type == "Outsourced",
        Employee.status == "Active",
        Employee.is_currently_assigned == False  # noqa: E712
    ).to_list()

    return {
        "total_available": len(available_workers),
        "workers": [
            {
                "id": w.uid,
                "name": w.name,
                "designation": w.designation,
                "phone_kuwait": w.phone_kuwait,
                "agency_name": w.agency_name,
                "daily_rate": w.basic_salary,
                "hourly_rate": w.default_hourly_rate,
                "availability_status": w.availability_status,
            }
            for w in available_workers
        ]
    }


@router.get("/workers")
async def get_all_temp_workers(
    available_only: Optional[bool] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all temporary/outsourced workers, optionally filtered by availability."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view workers")

    filters = [Employee.employee_type == "Outsourced"]

    if available_only is True:
        filters.append(Employee.is_currently_assigned == False)  # noqa: E712
    elif available_only is False:
        filters.append(Employee.is_currently_assigned == True)  # noqa: E712

    workers = await Employee.find(*filters).to_list()

    return {
        "total": len(workers),
        "workers": [
            {
                "id": w.uid,
                "name": w.name,
                "designation": w.designation,
                "phone_kuwait": w.phone_kuwait,
                "agency_name": w.agency_name,
                "daily_rate": w.basic_salary,
                "hourly_rate": w.default_hourly_rate,
                "availability_status": w.availability_status,
                "is_currently_assigned": w.is_currently_assigned,
                "current_site_id": w.current_site_id,
                "current_site_name": w.current_site_name,
                "status": w.status,
            }
            for w in workers
        ]
    }


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

    # Build temp assignment filters
    temp_filters = [TemporaryAssignment.status == "Active"]
    if site_id:
        temp_filters.append(TemporaryAssignment.site_id == site_id)
    if project_id:
        temp_filters.append(TemporaryAssignment.project_id == project_id)

    temp_assignments = await TemporaryAssignment.find(*temp_filters).to_list()

    # Calculate external labor costs
    external_cost_breakdown = []
    total_external_cost = 0.0

    for ta in temp_assignments:
        cost = calculate_cost(
            ta.rate_type, ta.daily_rate, ta.hourly_rate,
            ta.start_date, ta.end_date
        )
        total_external_cost += cost
        external_cost_breakdown.append({
            "assignment_id": ta.uid,
            "worker_name": ta.employee_name,
            "site_name": ta.site_name,
            "rate_type": ta.rate_type,
            "rate": ta.daily_rate if ta.rate_type == "Daily" else ta.hourly_rate,
            "start_date": ta.start_date.isoformat(),
            "end_date": ta.end_date.isoformat(),
            "total_days": ta.total_days,
            "cost": round(cost, 3),
        })

    # Calculate company labor costs from permanent assignments
    company_filters = []
    if site_id:
        company_filters.append(Employee.current_site_id == site_id)
    company_employees = await Employee.find(
        Employee.employee_type == "Company",
        Employee.is_currently_assigned == True,  # noqa: E712
        *company_filters
    ).to_list()

    total_company_cost = sum(
        (e.basic_salary + e.allowance) for e in company_employees
    )

    total_labor_cost = total_company_cost + total_external_cost
    external_percentage = (
        round(total_external_cost / total_labor_cost * 100, 2)
        if total_labor_cost > 0 else 0.0
    )

    return {
        "total_company_employees": len(company_employees),
        "total_company_cost": round(total_company_cost, 3),
        "total_external_workers": len(temp_assignments),
        "total_external_cost": round(total_external_cost, 3),
        "total_labor_cost": round(total_labor_cost, 3),
        "external_labor_percentage": external_percentage,
        "external_cost_breakdown": external_cost_breakdown,
    }


@router.post("/register-worker", status_code=status.HTTP_201_CREATED)
async def register_temp_worker(
    worker_data: RegisterTempWorkerCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Register a new temporary/outsourced worker."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can register workers")

    new_uid = await get_next_uid("employees")

    # Auto-generate employee code if not provided
    employee_code = worker_data.employee_code or f"EXT-{new_uid:03d}"

    new_worker = Employee(
        uid=new_uid,
        name=worker_data.name,
        designation=worker_data.designation,
        employee_type="Outsourced",
        phone_kuwait=worker_data.phone_kuwait,
        agency_name=worker_data.agency_name,
        basic_salary=worker_data.daily_rate or 0.0,      # Store daily rate in basic_salary
        default_hourly_rate=worker_data.hourly_rate or 0.0,
        status="Active",
        availability_status="Available",
        is_currently_assigned=False,
    )

    await new_worker.insert()

    logger.info(f"Registered new temp worker: {worker_data.name} (ID: {new_uid})")

    return {
        "id": new_uid,
        "name": new_worker.name,
        "designation": new_worker.designation,
        "employee_type": new_worker.employee_type,
        "phone_kuwait": new_worker.phone_kuwait,
        "agency_name": new_worker.agency_name,
        "daily_rate": new_worker.basic_salary,
        "hourly_rate": new_worker.default_hourly_rate,
        "availability_status": new_worker.availability_status,
        "employee_code": employee_code,
        "message": f"Worker {worker_data.name} registered successfully"
    }


@router.post("/assign-workers", status_code=status.HTTP_201_CREATED)
async def bulk_assign_temp_workers(
    assignment_data: BulkTempAssignmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk assign multiple temp workers to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign workers")

    site = await Site.find_one(Site.uid == assignment_data.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    project = await Project.find_one(Project.uid == site.project_id) if site.project_id else None
    contract = await Contract.find_one(Contract.uid == site.contract_id) if site.contract_id else None

    created_assignments = []
    failed_assignments = []
    total_estimated_cost = 0.0

    for worker_item in assignment_data.workers:
        try:
            employee = await Employee.find_one(Employee.uid == worker_item.employee_id)
            if not employee:
                failed_assignments.append({
                    "employee_id": worker_item.employee_id,
                    "reason": "Worker not found"
                })
                continue

            if employee.employee_type != "Outsourced":
                failed_assignments.append({
                    "employee_id": worker_item.employee_id,
                    "employee_name": employee.name,
                    "reason": "Worker is not an outsourced employee"
                })
                continue

            # Check for overlapping assignments
            overlapping = await TemporaryAssignment.find_one(
                TemporaryAssignment.employee_id == worker_item.employee_id,
                TemporaryAssignment.status == "Active",
                TemporaryAssignment.start_date <= worker_item.end_date,
                TemporaryAssignment.end_date >= worker_item.start_date
            )
            if overlapping:
                failed_assignments.append({
                    "employee_id": worker_item.employee_id,
                    "employee_name": employee.name,
                    "reason": "Worker has an overlapping assignment in this period"
                })
                continue

            if worker_item.end_date < worker_item.start_date:
                failed_assignments.append({
                    "employee_id": worker_item.employee_id,
                    "employee_name": employee.name,
                    "reason": "End date must be after start date"
                })
                continue

            # Determine rates
            rate_type = worker_item.rate_type or "Daily"
            daily_rate = worker_item.daily_rate if worker_item.daily_rate is not None else employee.basic_salary
            hourly_rate = worker_item.hourly_rate if worker_item.hourly_rate is not None else employee.default_hourly_rate

            total_days = (worker_item.end_date - worker_item.start_date).days + 1
            cost = calculate_cost(rate_type, daily_rate, hourly_rate, worker_item.start_date, worker_item.end_date, worker_item.total_hours)
            total_estimated_cost += cost

            new_uid = await get_next_uid("temporary_assignments")
            new_assignment = TemporaryAssignment(
                uid=new_uid,
                employee_id=worker_item.employee_id,
                employee_name=employee.name,
                employee_type="Outsourced",
                employee_designation=employee.designation,
                site_id=assignment_data.site_id,
                site_name=site.name,
                project_id=site.project_id or 0,
                manager_id=site.assigned_manager_id or 0,
                replacing_employee_id=assignment_data.replacing_employee_id,
                replacing_employee_name=assignment_data.replacing_employee_name,
                replacement_reason=assignment_data.replacement_reason,
                start_date=worker_item.start_date,
                end_date=worker_item.end_date,
                total_days=total_days,
                rate_type=rate_type,
                daily_rate=daily_rate,
                hourly_rate=hourly_rate,
                status="Active",
                created_by_admin_id=current_user.get("id")
            )

            await new_assignment.insert()

            # Update employee assignment state
            employee.is_currently_assigned = True
            employee.current_assignment_type = "Temporary"
            employee.current_project_id = site.project_id
            employee.current_project_name = project.project_name if project else None
            employee.current_site_id = assignment_data.site_id
            employee.current_site_name = site.name
            employee.current_manager_id = site.assigned_manager_id
            employee.current_manager_name = site.assigned_manager_name
            employee.current_assignment_start = worker_item.start_date
            employee.current_assignment_end = worker_item.end_date
            employee.availability_status = "Assigned"

            if new_assignment.uid not in employee.assignment_history_ids:
                employee.assignment_history_ids.append(new_assignment.uid)

            await employee.save()

            # Update site's assigned employees
            if worker_item.employee_id not in site.assigned_employee_ids:
                site.assigned_employee_ids.append(worker_item.employee_id)
            await site.update_workforce_count()

            created_assignments.append({
                "assignment_id": new_uid,
                "employee_id": worker_item.employee_id,
                "employee_name": employee.name,
                "start_date": worker_item.start_date.isoformat(),
                "end_date": worker_item.end_date.isoformat(),
                "total_days": total_days,
                "rate_type": rate_type,
                "rate": daily_rate if rate_type == "Daily" else hourly_rate,
                "estimated_cost": round(cost, 3),
            })

            logger.info(f"Temp worker '{employee.name}' assigned to site '{site.name}'")

        except Exception as e:
            logger.error("Error assigning temp worker: assignment failed", exc_info=True)
            failed_assignments.append({
                "employee_id": worker_item.employee_id,
                "reason": "An error occurred during assignment"
            })

    return {
        "message": f"{len(created_assignments)} temp workers assigned successfully",
        "created_count": len(created_assignments),
        "failed_count": len(failed_assignments),
        "total_estimated_cost": round(total_estimated_cost, 3),
        "assignments": created_assignments,
        "failures": failed_assignments,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def assign_single_temp_worker(
    assignment_data: SingleTempAssignmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign a single temporary worker to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign workers")

    bulk_data = BulkTempAssignmentCreate(
        site_id=assignment_data.site_id,
        workers=[
            TempWorkerAssignmentItem(
                employee_id=assignment_data.employee_id,
                start_date=assignment_data.start_date,
                end_date=assignment_data.end_date,
                rate_type=assignment_data.rate_type,
                daily_rate=assignment_data.daily_rate,
                hourly_rate=assignment_data.hourly_rate,
                total_hours=assignment_data.total_hours,
            )
        ],
        replacement_reason=assignment_data.replacement_reason,
        replacing_employee_id=assignment_data.replacing_employee_id,
        replacing_employee_name=assignment_data.replacing_employee_name,
    )

    result = await bulk_assign_temp_workers(bulk_data, current_user)

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

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    active_assignments = await TemporaryAssignment.find(
        TemporaryAssignment.site_id == site_id,
        TemporaryAssignment.status == "Active"
    ).to_list()

    cost_breakdown = []
    total_cost = 0.0

    for ta in active_assignments:
        cost = calculate_cost(
            ta.rate_type, ta.daily_rate, ta.hourly_rate,
            ta.start_date, ta.end_date
        )
        total_cost += cost
        cost_breakdown.append({
            "assignment_id": ta.uid,
            "employee_id": ta.employee_id,
            "employee_name": ta.employee_name,
            "designation": ta.employee_designation,
            "rate_type": ta.rate_type,
            "rate": ta.daily_rate if ta.rate_type == "Daily" else ta.hourly_rate,
            "start_date": ta.start_date.isoformat(),
            "end_date": ta.end_date.isoformat(),
            "total_days": ta.total_days,
            "replacement_reason": ta.replacement_reason,
            "estimated_cost": round(cost, 3),
            "status": ta.status,
        })

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total_temp_workers": len(active_assignments),
        "total_cost": round(total_cost, 3),
        "assignments": cost_breakdown,
    }


@router.get("/worker/{worker_id}/history")
async def get_worker_assignment_history(
    worker_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get assignment history for a temporary worker."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view worker history")

    worker = await Employee.find_one(Employee.uid == worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    assignments = await TemporaryAssignment.find(
        TemporaryAssignment.employee_id == worker_id
    ).sort("-created_at").to_list()

    total_days_worked = sum(a.total_days for a in assignments if a.status == "Completed")
    total_earnings = sum(
        calculate_cost(a.rate_type, a.daily_rate, a.hourly_rate, a.start_date, a.end_date)
        for a in assignments if a.status == "Completed"
    )

    return {
        "worker": {
            "id": worker.uid,
            "name": worker.name,
            "designation": worker.designation,
            "agency_name": worker.agency_name,
            "daily_rate": worker.basic_salary,
            "hourly_rate": worker.default_hourly_rate,
        },
        "total_assignments": len(assignments),
        "active_assignments": len([a for a in assignments if a.status == "Active"]),
        "completed_assignments": len([a for a in assignments if a.status == "Completed"]),
        "total_days_worked": total_days_worked,
        "total_earnings": round(total_earnings, 3),
        "assignments": [
            {
                "assignment_id": a.uid,
                "site_name": a.site_name,
                "start_date": a.start_date.isoformat(),
                "end_date": a.end_date.isoformat(),
                "total_days": a.total_days,
                "rate_type": a.rate_type,
                "rate": a.daily_rate if a.rate_type == "Daily" else a.hourly_rate,
                "status": a.status,
                "replacement_reason": a.replacement_reason,
            }
            for a in assignments
        ],
    }


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

    filters = []

    if site_id:
        filters.append(TemporaryAssignment.site_id == site_id)
    if status:
        filters.append(TemporaryAssignment.status == status)
    if start_after:
        filters.append(TemporaryAssignment.start_date >= start_after)
    if end_before:
        filters.append(TemporaryAssignment.end_date <= end_before)

    if filters:
        assignments = await TemporaryAssignment.find(*filters).sort("-created_at").to_list()
    else:
        assignments = await TemporaryAssignment.find_all().sort("-created_at").to_list()

    result = []
    for ta in assignments:
        cost = calculate_cost(
            ta.rate_type, ta.daily_rate, ta.hourly_rate,
            ta.start_date, ta.end_date
        )
        result.append({
            "assignment_id": ta.uid,
            "employee_id": ta.employee_id,
            "employee_name": ta.employee_name,
            "designation": ta.employee_designation,
            "site_id": ta.site_id,
            "site_name": ta.site_name,
            "start_date": ta.start_date.isoformat(),
            "end_date": ta.end_date.isoformat(),
            "total_days": ta.total_days,
            "rate_type": ta.rate_type,
            "rate": ta.daily_rate if ta.rate_type == "Daily" else ta.hourly_rate,
            "estimated_cost": round(cost, 3),
            "status": ta.status,
            "replacement_reason": ta.replacement_reason,
        })

    logger.info(f"Retrieved {len(result)} temp assignments")
    return result


@router.get("/{assignment_id}")
async def get_temp_assignment_details(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get details of a specific temporary assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignment details")

    assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    worker = await Employee.find_one(Employee.uid == assignment.employee_id)
    site = await Site.find_one(Site.uid == assignment.site_id)

    cost = calculate_cost(
        assignment.rate_type, assignment.daily_rate, assignment.hourly_rate,
        assignment.start_date, assignment.end_date
    )

    return {
        "assignment": {
            "assignment_id": assignment.uid,
            "employee_id": assignment.employee_id,
            "employee_name": assignment.employee_name,
            "designation": assignment.employee_designation,
            "site_id": assignment.site_id,
            "site_name": assignment.site_name,
            "start_date": assignment.start_date.isoformat(),
            "end_date": assignment.end_date.isoformat(),
            "total_days": assignment.total_days,
            "rate_type": assignment.rate_type,
            "daily_rate": assignment.daily_rate,
            "hourly_rate": assignment.hourly_rate,
            "estimated_cost": round(cost, 3),
            "status": assignment.status,
            "replacement_reason": assignment.replacement_reason,
            "created_at": assignment.created_at.isoformat(),
        },
        "worker": worker,
        "site": site,
    }


@router.put("/{assignment_id}")
async def update_temp_assignment(
    assignment_id: int,
    update_data: TempAssignmentUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update a temporary assignment (dates, rates, status)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update assignments")

    assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    update_dict = update_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(assignment, key, value)

    # Recalculate total_days if dates changed
    if "start_date" in update_dict or "end_date" in update_dict:
        assignment.total_days = (assignment.end_date - assignment.start_date).days + 1

    assignment.updated_at = datetime.now()
    await assignment.save()

    cost = calculate_cost(
        assignment.rate_type, assignment.daily_rate, assignment.hourly_rate,
        assignment.start_date, assignment.end_date
    )

    logger.info(f"Temp assignment {assignment_id} updated")

    return {
        "assignment_id": assignment.uid,
        "status": assignment.status,
        "start_date": assignment.start_date.isoformat(),
        "end_date": assignment.end_date.isoformat(),
        "total_days": assignment.total_days,
        "estimated_cost": round(cost, 3),
        "message": "Assignment updated successfully"
    }


@router.delete("/{assignment_id}", status_code=200)
async def end_temp_assignment(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """End a temporary assignment (set status to Completed)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can end assignments")

    assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    actual_end = date.today()

    # Calculate final cost
    cost = calculate_cost(
        assignment.rate_type, assignment.daily_rate, assignment.hourly_rate,
        assignment.start_date, actual_end
    )

    # Update assignment
    assignment.status = "Completed"
    assignment.end_date = actual_end
    assignment.total_days = (actual_end - assignment.start_date).days + 1
    assignment.updated_at = datetime.now()
    await assignment.save()

    # Update employee state
    worker = await Employee.find_one(Employee.uid == assignment.employee_id)
    if worker:
        # Check if employee has other active temp assignments
        other_active = await TemporaryAssignment.find(
            TemporaryAssignment.employee_id == assignment.employee_id,
            TemporaryAssignment.status == "Active",
            TemporaryAssignment.uid != assignment_id
        ).count()

        if other_active == 0:
            worker.is_currently_assigned = False
            worker.current_assignment_type = None
            worker.current_project_id = None
            worker.current_site_id = None
            worker.current_manager_id = None
            worker.availability_status = "Available"

        await worker.save()

    # Update site's assigned employees
    site = await Site.find_one(Site.uid == assignment.site_id)
    if site:
        if assignment.employee_id in site.assigned_employee_ids:
            site.assigned_employee_ids.remove(assignment.employee_id)
        await site.update_workforce_count()

    logger.info(f"Temp assignment for worker '{assignment.employee_name}' ended successfully")

    return {
        "message": "Assignment ended successfully",
        "assignment_id": assignment_id,
        "worker_name": assignment.employee_name,
        "actual_end_date": actual_end.isoformat(),
        "total_days": assignment.total_days,
        "final_cost": round(cost, 3),
    }
