# backend/routers/workflow_sites.py

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.workflow_site_service import WorkflowSiteService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/workflow/sites",
    tags=["Workflow Sites"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("WorkflowSitesRouter", log_file="logs/workflow_sites_router.log", level=logging.DEBUG)
service = WorkflowSiteService()

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

class MultiManagerAssignment(BaseModel):
    manager_ids: List[int]

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
    return await service.get_available_managers(current_user)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_site(
    site_data: SiteCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new site under a contract and project."""
    result = await service.create_site(site_data, current_user)
    logger.info("Site created for project %s", site_data.project_id)
    return result


@router.get("/", response_model=List[dict])
async def get_all_sites(
    project_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all sites. Optionally filter by project_id, contract_id, or status."""
    result = await service.get_all_sites(current_user, project_id=project_id, contract_id=contract_id, status_filter=status)
    logger.info("Retrieved %d sites", len(result))
    return result


@router.get("/{site_id}")
async def get_site_details(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed information about a specific site."""
    return await service.get_site_details(site_id, current_user)


@router.put("/{site_id}")
async def update_site(
    site_id: int,
    site_update: SiteUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update site details."""
    result = await service.update_site(site_id, site_update, current_user)
    logger.info("Site %s updated", site_id)
    return result


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a site. Only allowed if no active assignments exist."""
    await service.delete_site(site_id, current_user)
    logger.info("Site %s deleted", site_id)
    return None


# ===== MANAGER ASSIGNMENT =====

@router.post("/{site_id}/assign-manager")
async def assign_manager_to_site(
    site_id: int,
    assignment: ManagerAssignment,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign a site manager to a site."""
    result = await service.assign_manager(site_id, assignment.manager_id, current_user)
    logger.info("Manager %s assigned to site %s", assignment.manager_id, site_id)
    return result


@router.delete("/{site_id}/unassign-manager", status_code=204)
async def unassign_manager_from_site(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Remove manager assignment from a site."""
    await service.unassign_manager(site_id, current_user)
    logger.info("Manager unassigned from site %s", site_id)
    return None


@router.post("/{site_id}/add-manager")
async def add_manager_to_site(
    site_id: int,
    assignment: ManagerAssignment,
    current_user: dict = Depends(get_current_active_user)
):
    """Add an additional manager to a site (multi-manager support)."""
    result = await service.add_manager(site_id, assignment.manager_id, current_user)
    logger.info("Manager %s added to site %s", assignment.manager_id, site_id)
    return result


@router.delete("/{site_id}/remove-manager/{manager_id}", status_code=204)
async def remove_manager_from_site(
    site_id: int,
    manager_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Remove a specific manager from a site's manager list."""
    await service.remove_manager(site_id, manager_id, current_user)
    logger.info("Manager %s removed from site %s", manager_id, site_id)
    return None


# ===== EMPLOYEE ASSIGNMENT FOR SITES =====

@router.get("/{site_id}/employees")
async def get_site_employees(
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all employees assigned to a site."""
    return await service.get_site_employees(site_id, current_user)


@router.post("/{site_id}/assign-employees", status_code=status.HTTP_201_CREATED)
async def assign_employees_to_site(
    site_id: int,
    request: EmployeeAssignRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Assign employees to a site."""
    result = await service.assign_employees(site_id, request, current_user)
    logger.info("%d employees assigned to site %s", result["created_count"], site_id)
    return result


@router.delete("/{site_id}/employees/{employee_id}", status_code=204)
async def remove_employee_from_site(
    site_id: int,
    employee_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Remove an employee from a site."""
    await service.remove_employee(site_id, employee_id, current_user)
    logger.info("Employee %s removed from site %s", employee_id, site_id)
    return None


@router.get("/{site_id}/activity")
async def get_site_activity(
    site_id: int,
    limit: int = 20,
    current_user: dict = Depends(get_current_active_user)
):
    """Get recent activity log for a specific site."""
    return await service.get_site_activity(site_id, limit, current_user)

