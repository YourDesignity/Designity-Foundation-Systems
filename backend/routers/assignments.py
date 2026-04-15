# backend/routers/assignments.py

import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import (
    EmployeeAssignment, Employee, Site, Project,
    Contract, Admin
)
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/assignments",
    tags=["Employee Assignments"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("AssignmentsRouter", log_file="logs/assignments_router.log", level=logging.DEBUG)

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

    # Verify site exists
    site = await Site.find_one(Site.uid == assignment_data.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Get project and contract info
    project = await Project.find_one(Project.uid == site.project_id) if site.project_id else None
    contract = await Contract.find_one(Contract.uid == site.contract_id) if site.contract_id else None

    created_assignments = []
    failed_assignments = []

    for emp_id in assignment_data.employee_ids:
        try:
            # Verify employee exists
            employee = await Employee.find_one(Employee.uid == emp_id)
            if not employee:
                failed_assignments.append({
                    "employee_id": emp_id,
                    "reason": "Employee not found"
                })
                continue

            # Check if employee is already assigned to this site
            existing = await EmployeeAssignment.find_one(
                EmployeeAssignment.employee_id == emp_id,
                EmployeeAssignment.site_id == assignment_data.site_id,
                EmployeeAssignment.status == "Active"
            )

            if existing:
                failed_assignments.append({
                    "employee_id": emp_id,
                    "employee_name": employee.name,
                    "reason": "Already assigned to this site"
                })
                continue

            # Create assignment
            new_uid = await get_next_uid("employee_assignments")

            new_assignment = EmployeeAssignment(
                uid=new_uid,
                employee_id=emp_id,
                employee_name=employee.name,
                employee_designation=employee.designation,
                employee_type="Company",
                assignment_type="Permanent",
                project_id=site.project_id,
                project_name=project.project_name if project else None,
                contract_id=site.contract_id,
                site_id=assignment_data.site_id,
                site_name=site.name,
                manager_id=site.assigned_manager_id,
                manager_name=site.assigned_manager_name,
                assigned_date=date.today(),
                assignment_start=assignment_data.assignment_start,
                assignment_end=assignment_data.assignment_end,
                status="Active",
                created_by_admin_id=current_user.get("id")
            )

            await new_assignment.insert()

            # Update employee's current assignment info
            employee.is_currently_assigned = True
            employee.current_assignment_type = "Permanent"
            employee.current_project_id = site.project_id
            employee.current_project_name = project.project_name if project else None
            employee.current_site_id = assignment_data.site_id
            employee.current_site_name = site.name
            employee.current_manager_id = site.assigned_manager_id
            employee.current_manager_name = site.assigned_manager_name
            employee.current_assignment_start = assignment_data.assignment_start
            employee.current_assignment_end = assignment_data.assignment_end
            employee.availability_status = "Assigned"

            if new_assignment.uid not in employee.assignment_history_ids:
                employee.assignment_history_ids.append(new_assignment.uid)

            await employee.save()

            # Update site's assigned employees
            if emp_id not in site.assigned_employee_ids:
                site.assigned_employee_ids.append(emp_id)

            await site.update_workforce_count()

            created_assignments.append(new_assignment)

            logger.info(f"Employee ID {emp_id} assigned to site ID {assignment_data.site_id}")

        except Exception as e:
            logger.error(f"Error assigning employee {emp_id}: {str(e)}")
            failed_assignments.append({
                "employee_id": emp_id,
                "reason": "An error occurred during assignment"
            })

    return {
        "message": f"{len(created_assignments)} employees assigned successfully",
        "created_count": len(created_assignments),
        "failed_count": len(failed_assignments),
        "assignments": created_assignments,
        "failures": failed_assignments
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def assign_single_employee(
    assignment_data: SingleAssignmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign a single employee to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign employees")

    # Use bulk assignment with single employee
    bulk_data = BulkAssignmentCreate(
        site_id=assignment_data.site_id,
        employee_ids=[assignment_data.employee_id],
        assignment_start=assignment_data.assignment_start,
        assignment_end=assignment_data.assignment_end
    )

    result = await bulk_assign_employees(bulk_data, current_user)

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

    # Get company employees who are not currently assigned
    available_employees = await Employee.find(
        Employee.employee_type == "Company",
        Employee.status == "Active",
        Employee.is_currently_assigned == False  # noqa: E712 - Beanie ODM requires == for query building
    ).to_list()

    return {
        "total_available": len(available_employees),
        "employees": available_employees
    }


@router.get("/employee/{employee_id}/history")
async def get_employee_assignment_history(
    employee_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get assignment history for an employee."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignment history")

    employee = await Employee.find_one(Employee.uid == employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    assignments = await EmployeeAssignment.find(
        EmployeeAssignment.employee_id == employee_id
    ).sort("-created_at").to_list()

    return {
        "employee": employee,
        "total_assignments": len(assignments),
        "active_assignments": len([a for a in assignments if a.status == "Active"]),
        "completed_assignments": len([a for a in assignments if a.status == "Completed"]),
        "assignments": assignments
    }


@router.get("/site/{site_id}/employees")
async def get_site_assignments(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all employees assigned to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view site assignments")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    assignments = await EmployeeAssignment.find(
        EmployeeAssignment.site_id == site_id,
        EmployeeAssignment.status == "Active"
    ).to_list()

    employees = []
    for assignment in assignments:
        emp = await Employee.find_one(Employee.uid == assignment.employee_id)
        if emp:
            employees.append(emp)

    return {
        "site": site,
        "required_workers": site.required_workers,
        "assigned_workers": site.assigned_workers,
        "capacity_percentage": round(site.assigned_workers / site.required_workers * 100, 2) if site.required_workers > 0 else 0,
        "assignments": assignments,
        "employees": employees
    }


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

    filters = []

    if site_id:
        filters.append(EmployeeAssignment.site_id == site_id)
    if project_id:
        filters.append(EmployeeAssignment.project_id == project_id)
    if employee_id:
        filters.append(EmployeeAssignment.employee_id == employee_id)
    if status:
        filters.append(EmployeeAssignment.status == status)

    if filters:
        assignments = await EmployeeAssignment.find(*filters).sort("-created_at").to_list()
    else:
        assignments = await EmployeeAssignment.find_all().sort("-created_at").to_list()

    logger.info(f"Retrieved {len(assignments)} assignments")
    return assignments


@router.get("/{assignment_id}")
async def get_assignment_details(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get details of a specific assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view assignment details")

    assignment = await EmployeeAssignment.find_one(EmployeeAssignment.uid == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Get related data
    employee = await Employee.find_one(Employee.uid == assignment.employee_id)
    site = await Site.find_one(Site.uid == assignment.site_id)

    return {
        "assignment": assignment,
        "employee": employee,
        "site": site
    }


@router.put("/{assignment_id}")
async def update_assignment(
    assignment_id: int,
    assignment_update: AssignmentUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update assignment details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update assignments")

    assignment = await EmployeeAssignment.find_one(EmployeeAssignment.uid == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    update_data = assignment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assignment, key, value)

    assignment.updated_at = datetime.now()
    await assignment.save()

    logger.info(f"Assignment {assignment_id} updated")

    return assignment


@router.delete("/{assignment_id}", status_code=204)
async def unassign_employee(
    assignment_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Unassign an employee from a site (end the assignment)."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can unassign employees")

    assignment = await EmployeeAssignment.find_one(EmployeeAssignment.uid == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Update assignment status
    assignment.status = "Completed"
    assignment.assignment_end = date.today()
    assignment.updated_at = datetime.now()
    await assignment.save()

    # Update employee's current assignment status
    employee = await Employee.find_one(Employee.uid == assignment.employee_id)
    if employee:
        # Check if employee has other active assignments
        other_active = await EmployeeAssignment.find(
            EmployeeAssignment.employee_id == assignment.employee_id,
            EmployeeAssignment.status == "Active",
            EmployeeAssignment.uid != assignment_id
        ).count()

        if other_active == 0:
            employee.is_currently_assigned = False
            employee.current_assignment_type = None
            employee.current_project_id = None
            employee.current_site_id = None
            employee.current_manager_id = None
            employee.availability_status = "Available"

        await employee.save()

    # Update site's assigned employees
    site = await Site.find_one(Site.uid == assignment.site_id)
    if site:
        if assignment.employee_id in site.assigned_employee_ids:
            site.assigned_employee_ids.remove(assignment.employee_id)

        await site.update_workforce_count()

    logger.info(f"Employee ID {assignment.employee_id} unassigned from site ID {assignment.site_id}")

    return None
