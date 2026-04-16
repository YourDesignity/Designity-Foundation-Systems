# backend/routers/projects.py

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import Project, Contract, Site, EmployeeAssignment
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("ProjectsRouter", log_file="logs/projects_router.log", level=logging.DEBUG)

# ===== SCHEMAS =====

class ProjectCreate(BaseModel):
    project_name: str
    client_name: str
    client_contact: Optional[str] = None
    client_email: Optional[str] = None
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    client_email: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # Active | Completed | On Hold | Cancelled

class ProjectResponse(BaseModel):
    uid: int
    project_code: str
    project_name: str
    client_name: str
    client_contact: Optional[str]
    client_email: Optional[str]
    description: Optional[str]
    status: str
    total_sites: int
    total_assigned_employees: int
    total_assigned_managers: int
    created_at: datetime
    updated_at: datetime

# ===== ENDPOINTS =====

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new project. Only Admins can create projects."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create projects")

    from backend.models import CompanySettings

    settings = await CompanySettings.find_one(CompanySettings.uid == 1)

    new_uid = await get_next_uid("projects")
    if settings and settings.auto_generate_project_codes:
        prefix = settings.project_code_prefix or "PRJ"
        project_code = f"{prefix}-{new_uid:03d}"
    else:
        project_code = f"PRJ-{new_uid:03d}"

    new_project = Project(
        uid=new_uid,
        project_code=project_code,
        project_name=project_data.project_name,
        client_name=project_data.client_name,
        client_contact=project_data.client_contact,
        client_email=project_data.client_email,
        description=project_data.description,
        status="Active",
        created_by_admin_id=current_user.get("id")
    )

    await new_project.insert()

    logger.info(f"Project created: {project_code} by admin {current_user.get('sub')}")

    return new_project


@router.get("/", response_model=List[ProjectResponse])
async def get_all_projects(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all projects. Optionally filter by status."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view all projects")

    if status:
        projects = await Project.find(Project.status == status).sort("+uid").to_list()
    else:
        projects = await Project.find_all().sort("+uid").to_list()

    logger.info(f"Retrieved {len(projects)} projects")
    return projects


@router.get("/{project_id}")
async def get_project_details(
    project_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed information about a specific project including contracts and sites."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view project details")

    project = await Project.find_one(Project.uid == project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await project.update_metrics()

    contracts = await Contract.find(Contract.project_id == project_id).to_list()
    sites = await Site.find(Site.project_id == project_id).to_list()
    assignments = await EmployeeAssignment.find(
        EmployeeAssignment.project_id == project_id,
        EmployeeAssignment.status == "Active"
    ).to_list()

    return {
        "project": project,
        "contracts": contracts,
        "sites": sites,
        "active_assignments": assignments
    }


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update project details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update projects")

    project = await Project.find_one(Project.uid == project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.now()
    await project.save()

    logger.info(f"Project {project_id} updated by admin {current_user.get('sub')}")

    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a project. Only allowed if no active contracts/sites/assignments exist."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete projects")

    project = await Project.find_one(Project.uid == project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    active_contracts = await Contract.find(
        Contract.project_id == project_id,
        Contract.status == "Active"
    ).count()

    if active_contracts > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete project with {active_contracts} active contract(s). Complete or terminate contracts first."
        )

    active_sites = await Site.find(
        Site.project_id == project_id,
        Site.status == "Active"
    ).count()

    if active_sites > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete project with {active_sites} active site(s)."
        )

    await project.delete()
    logger.info(f"Project {project_id} deleted by admin {current_user.get('sub')}")

    return None


@router.get("/{project_id}/workforce-summary")
async def get_project_workforce_summary(
    project_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get workforce allocation summary for a project."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view workforce summary")

    project = await Project.find_one(Project.uid == project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sites = await Site.find(Site.project_id == project_id).to_list()

    total_required = sum(s.required_workers for s in sites)
    total_assigned = sum(s.assigned_workers for s in sites)

    company_assignments = await EmployeeAssignment.find(
        EmployeeAssignment.project_id == project_id,
        EmployeeAssignment.employee_type == "Company",
        EmployeeAssignment.status == "Active"
    ).count()

    from backend.models import TemporaryAssignment
    external_assignments = await TemporaryAssignment.find(
        TemporaryAssignment.project_id == project_id,
        TemporaryAssignment.status == "Active"
    ).count()

    return {
        "project_id": project_id,
        "project_name": project.project_name,
        "total_sites": len(sites),
        "total_required_workers": total_required,
        "total_assigned_workers": total_assigned,
        "company_employees": company_assignments,
        "external_workers": external_assignments,
        "fulfillment_rate": (total_assigned / total_required * 100) if total_required > 0 else 0
    }
