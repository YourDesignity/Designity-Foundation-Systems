# backend/routers/projects.py

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.projects.project_service import ProjectService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("ProjectsRouter", log_file="logs/projects_router.log", level=logging.DEBUG)
service = ProjectService()

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

    project = await service.create_project(project_data, current_user.get("id"))
    logger.info(f"Project created: {project.project_code} by admin {current_user.get('sub')}")
    return project


@router.get("/", response_model=List[ProjectResponse])
async def get_all_projects(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all projects. Optionally filter by status."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view all projects")

    projects = await service.get_projects_filtered(status)
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

    return await service.get_project_details(project_id)


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update project details."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update projects")

    project = await service.update_project(project_id, project_update)
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

    await service.delete_project_with_constraints(project_id)
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

    return await service.get_project_workforce_summary(project_id)
