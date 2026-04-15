# backend/routers/workflow_sites.py

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import Project, Contract, Site, Admin
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/workflow/sites",
    tags=["Workflow Sites"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("WorkflowSitesRouter", log_file="logs/workflow_sites_router.log", level=logging.DEBUG)

# ===== SCHEMAS =====

class SiteCreate(BaseModel):
    site_name: str
    location: str
    description: Optional[str] = None
    project_id: int
    contract_id: int
    required_workers: int = 0

class SiteUpdate(BaseModel):
    site_name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    required_workers: Optional[int] = None
    status: Optional[str] = None

class ManagerAssignment(BaseModel):
    manager_id: int

class EmployeeAssignRequest(BaseModel):
    employee_ids: List[int]
    assignment_start: str
    assignment_end: Optional[str] = None

# ===== ENDPOINTS =====

# NOTE: Static path endpoints (/managers, /available-employees) MUST be declared
# BEFORE dynamic path endpoints (/{site_id}) to prevent FastAPI from treating
# the literal string as an integer path parameter, causing 422 errors.

@router.get("/managers")
async def get_available_managers(
    current_user: dict = Depends(get_current_active_user)
):
    """Get list of site managers available for assignment."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view managers")

    managers = await Admin.find(Admin.role == "Site Manager", Admin.is_active == True).to_list()
    return [
        {
            "uid": m.uid,
            "full_name": m.full_name,
            "email": m.email,
            "role": m.role,
        }
        for m in managers
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_site(
    site_data: SiteCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new site under a contract and project."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create sites")

    project = await Project.find_one(Project.uid == site_data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    contract = await Contract.find_one(Contract.uid == site_data.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.project_id != site_data.project_id:
        raise HTTPException(
            status_code=400,
            detail="Contract does not belong to the specified project"
        )

    from backend.models import CompanySettings
    settings = await CompanySettings.find_one(CompanySettings.uid == 1)

    new_uid = await get_next_uid("sites")
    if settings and settings.auto_generate_site_codes:
        prefix = settings.site_code_prefix or "SITE"
        site_code = f"{prefix}-{new_uid:03d}"
    else:
        site_code = f"SITE-{new_uid:03d}"

    new_site = Site(
        uid=new_uid,
        site_code=site_code,
        name=site_data.site_name,
        location=site_data.location,
        description=site_data.description,
        project_id=site_data.project_id,
        project_name=project.project_name,
        contract_id=site_data.contract_id,
        contract_code=contract.contract_code,
        required_workers=site_data.required_workers,
        status="Active"
    )

    await new_site.insert()

    if new_site.uid not in project.site_ids:
        project.site_ids.append(new_site.uid)
        await project.save()

    if new_site.uid not in contract.site_ids:
        contract.site_ids.append(new_site.uid)
        await contract.save()

    logger.info(f"Site created: {site_code} for project {project.project_code}")

    return new_site.model_dump(mode='json')


@router.get("/", response_model=List[dict])
async def get_all_sites(
    project_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all sites. Optionally filter by project_id, contract_id, or status."""
    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me:
            raise HTTPException(status_code=404, detail="Manager profile not found")

        sites = await Site.find(Site.assigned_manager_id == me.uid).to_list()

    elif current_user.get("role") in ["SuperAdmin", "Admin"]:
        filters = []
        if project_id:
            filters.append(Site.project_id == project_id)
        if contract_id:
            filters.append(Site.contract_id == contract_id)
        if status:
            filters.append(Site.status == status)

        if filters:
            sites = await Site.find(*filters).sort("+uid").to_list()
        else:
            sites = await Site.find_all().sort("+uid").to_list()

    else:
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Retrieved {len(sites)} sites")
    return [s.model_dump(mode='json') for s in sites]


@router.get("/{site_id}")
async def get_site_details(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed information about a specific site."""
    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or site.assigned_manager_id != me.uid:
            raise HTTPException(status_code=403, detail="Access denied")

    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    from backend.models import EmployeeAssignment, Employee
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
        "site": site.model_dump(mode='json'),
        "assigned_employees": [e.model_dump(mode='json') for e in employees],
        "assignments": [a.model_dump(mode='json') for a in assignments]
    }


@router.put("/{site_id}")
async def update_site(
    site_id: int,
    site_update: SiteUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update site details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update sites")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    update_data = site_update.model_dump(exclude_unset=True)
    # Map site_name -> name for the Site model
    if "site_name" in update_data:
        update_data["name"] = update_data.pop("site_name")
    for key, value in update_data.items():
        setattr(site, key, value)

    await site.save()

    logger.info(f"Site {site_id} updated")

    return site.model_dump(mode='json')


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a site. Only allowed if no active assignments exist."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete sites")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    from backend.models import EmployeeAssignment
    active_assignments = await EmployeeAssignment.find(
        EmployeeAssignment.site_id == site_id,
        EmployeeAssignment.status == "Active"
    ).count()

    if active_assignments > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete site with {active_assignments} active employee assignment(s)."
        )

    if site.project_id:
        project = await Project.find_one(Project.uid == site.project_id)
        if project and site.uid in project.site_ids:
            project.site_ids.remove(site.uid)
            await project.save()

    if site.contract_id:
        contract = await Contract.find_one(Contract.uid == site.contract_id)
        if contract and site.uid in contract.site_ids:
            contract.site_ids.remove(site.uid)
            await contract.save()

    await site.delete()
    logger.info(f"Site {site_id} deleted")

    return None


# ===== MANAGER ASSIGNMENT =====

@router.post("/{site_id}/assign-manager")
async def assign_manager_to_site(
    site_id: int,
    assignment: ManagerAssignment,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign a site manager to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign managers")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    manager = await Admin.find_one(Admin.uid == assignment.manager_id)
    if not manager or manager.role != "Site Manager":
        raise HTTPException(status_code=400, detail="Invalid manager ID: must be an active Site Manager")

    site.assigned_manager_id = assignment.manager_id
    site.assigned_manager_name = manager.full_name
    await site.save()

    logger.info(f"Manager {manager.full_name} assigned to site {site.site_code}")

    return {
        "message": "Manager assigned successfully",
        "site_id": site_id,
        "site_name": site.name,
        "manager_id": assignment.manager_id,
        "manager_name": manager.full_name
    }


@router.delete("/{site_id}/unassign-manager", status_code=204)
async def unassign_manager_from_site(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Remove manager assignment from a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can unassign managers")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    site.assigned_manager_id = None
    site.assigned_manager_name = None
    await site.save()

    logger.info(f"Manager unassigned from site {site.site_code}")

    return None


# ===== EMPLOYEE ASSIGNMENT FOR SITES =====

@router.get("/{site_id}/employees")
async def get_site_employees(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all employees assigned to a site."""
    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or site.assigned_manager_id != me.uid:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    from backend.models import EmployeeAssignment, Employee
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
        "site": site.model_dump(mode='json'),
        "employees": [e.model_dump(mode='json') for e in employees],
        "assignments": [a.model_dump(mode='json') for a in assignments],
        "total_assigned": len(employees),
        "required_workers": site.required_workers,
    }


@router.post("/{site_id}/assign-employees", status_code=status.HTTP_201_CREATED)
async def assign_employees_to_site(
    site_id: int,
    request: EmployeeAssignRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign employees to a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can assign employees")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    from backend.models import EmployeeAssignment, Employee, Project
    from backend.database import get_next_uid
    from datetime import date, datetime as dt

    try:
        start = date.fromisoformat(request.assignment_start)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid assignment_start date format (use YYYY-MM-DD)")

    end = None
    if request.assignment_end:
        try:
            end = date.fromisoformat(request.assignment_end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid assignment_end date format (use YYYY-MM-DD)")

    project = await Project.find_one(Project.uid == site.project_id) if site.project_id else None
    created = []
    failed = []

    for emp_id in request.employee_ids:
        employee = await Employee.find_one(Employee.uid == emp_id)
        if not employee:
            failed.append({"employee_id": emp_id, "reason": "Employee not found"})
            continue

        existing = await EmployeeAssignment.find_one(
            EmployeeAssignment.employee_id == emp_id,
            EmployeeAssignment.site_id == site_id,
            EmployeeAssignment.status == "Active"
        )
        if existing:
            failed.append({"employee_id": emp_id, "employee_name": employee.name, "reason": "Already assigned to this site"})
            continue

        new_uid = await get_next_uid("employee_assignments")
        assignment = EmployeeAssignment(
            uid=new_uid,
            employee_id=emp_id,
            employee_name=employee.name,
            employee_designation=employee.designation,
            employee_type=employee.employee_type,
            assignment_type="Permanent",
            project_id=site.project_id,
            project_name=project.project_name if project else None,
            contract_id=site.contract_id,
            site_id=site_id,
            site_name=site.name,
            manager_id=site.assigned_manager_id,
            manager_name=site.assigned_manager_name,
            assigned_date=date.today(),
            assignment_start=start,
            assignment_end=end,
            status="Active",
            created_by_admin_id=current_user.get("id")
        )
        await assignment.insert()

        employee.is_currently_assigned = True
        employee.current_assignment_type = "Permanent"
        employee.current_project_id = site.project_id
        employee.current_project_name = project.project_name if project else None
        employee.current_site_id = site_id
        employee.current_site_name = site.name
        employee.current_manager_id = site.assigned_manager_id
        employee.current_manager_name = site.assigned_manager_name
        employee.current_assignment_start = start
        employee.current_assignment_end = end
        employee.availability_status = "Assigned"
        if assignment.uid not in employee.assignment_history_ids:
            employee.assignment_history_ids.append(assignment.uid)
        await employee.save()

        if emp_id not in site.assigned_employee_ids:
            site.assigned_employee_ids.append(emp_id)

        created.append(assignment.model_dump(mode='json'))

    await site.update_workforce_count()

    logger.info(f"{len(created)} employees assigned to site {site_id}")
    return {
        "message": f"{len(created)} employees assigned successfully",
        "created_count": len(created),
        "failed_count": len(failed),
        "assignments": created,
        "failures": failed,
    }


@router.delete("/{site_id}/employees/{employee_id}", status_code=204)
async def remove_employee_from_site(
    site_id: int,
    employee_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Remove an employee from a site."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can remove employees")

    from backend.models import EmployeeAssignment, Employee
    from datetime import date, datetime as dt

    assignment = await EmployeeAssignment.find_one(
        EmployeeAssignment.employee_id == employee_id,
        EmployeeAssignment.site_id == site_id,
        EmployeeAssignment.status == "Active"
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Active assignment not found for this employee at this site")

    assignment.status = "Completed"
    assignment.assignment_end = date.today()
    assignment.updated_at = dt.now()
    await assignment.save()

    employee = await Employee.find_one(Employee.uid == employee_id)
    if employee:
        other_active = await EmployeeAssignment.find(
            EmployeeAssignment.employee_id == employee_id,
            EmployeeAssignment.status == "Active",
        ).count()
        if other_active == 0:
            employee.is_currently_assigned = False
            employee.current_site_id = None
            employee.availability_status = "Available"
        await employee.save()

    site = await Site.find_one(Site.uid == site_id)
    if site:
        if employee_id in site.assigned_employee_ids:
            site.assigned_employee_ids.remove(employee_id)
        await site.update_workforce_count()

    logger.info(f"Employee removed from site {site_id}")
    return None


@router.get("/{site_id}/activity")
async def get_site_activity(
    site_id: int,
    limit: int = 20,
    current_user: dict = Depends(get_current_active_user)
):
    """Get recent activity log for a specific site."""
    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or site.assigned_manager_id != me.uid:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    from backend.models import EmployeeAssignment, TemporaryAssignment

    # Collect recent employee assignments
    emp_assignments = await EmployeeAssignment.find(
        EmployeeAssignment.site_id == site_id
    ).sort("-uid").limit(limit).to_list()

    # Collect recent temp assignments
    temp_assignments = await TemporaryAssignment.find(
        TemporaryAssignment.site_id == site_id
    ).sort("-uid").limit(limit).to_list()

    activities = []

    for a in emp_assignments:
        activities.append({
            "type": "employee_assigned" if a.status == "Active" else "employee_unassigned",
            "description": f"{a.employee_name} ({a.employee_designation}) assigned to this site",
            "date": a.assigned_date.isoformat() if a.assigned_date else (a.created_at.isoformat() if a.created_at else None),
            "status": a.status,
            "employee_name": a.employee_name,
            "employee_type": a.employee_type,
        })

    for t in temp_assignments:
        activities.append({
            "type": "temp_worker_assigned" if t.status == "Active" else "temp_worker_ended",
            "description": f"Temporary worker {t.employee_name} assigned to this site",
            "date": t.start_date.isoformat() if t.start_date else (t.created_at.isoformat() if t.created_at else None),
            "status": t.status,
            "employee_name": t.employee_name,
            "employee_type": "Temporary",
        })

    # Sort by date descending
    activities.sort(key=lambda x: x["date"] or "", reverse=True)

    return {
        "site_id": site_id,
        "site_name": site.name,
        "activities": activities[:limit],
        "total": len(activities),
    }
