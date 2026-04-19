# backend/routers/manager_sites.py

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services import ManagerService
from backend.services.manager_site_service import ManagerSiteService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/manager-sites",
    tags=["Manager Site Management"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("ManagerSitesRouter", log_file="logs/manager_sites_router.log", level=logging.DEBUG)
service = ManagerSiteService()
manager_service = ManagerService()


# ===== SCHEMAS =====

class AttendanceRecord(BaseModel):
    employee_uid: int
    status: str  # "Present" | "Absent" | "Late" | "Half Day" | "On Leave"
    shift: Optional[str] = "Morning"
    overtime_hours: Optional[int] = 0
    is_substitute: bool = False
    replacing_employee_id: Optional[int] = None
    leave_type: Optional[str] = None
    leave_reason: Optional[str] = None
    substitute_requested: bool = False
    notes: Optional[str] = None

class BulkAttendanceRequest(BaseModel):
    site_id: int
    date: str  # YYYY-MM-DD
    records: List[AttendanceRecord]


# ===== ENDPOINTS =====

@router.get("/{manager_id}/sites")
async def get_manager_sites(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all sites managed by a specific manager."""
    result = await manager_service.get_manager_sites_with_stats(manager_id, current_user)
    logger.info("Manager %s has %d sites", manager_id, result["total_sites"])
    return result


@router.get("/{manager_id}/sites/{site_id}/employees")
async def get_managed_site_employees(
    manager_id: int,
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all employees at a site managed by this manager."""
    return await manager_service.get_managed_site_employees(manager_id, site_id, current_user)


@router.post("/{manager_id}/sites/{site_id}/attendance", status_code=status.HTTP_201_CREATED)
async def record_site_attendance(
    manager_id: int,
    site_id: int,
    request: BulkAttendanceRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Record attendance for all employees at a managed site."""
    result = await service.record_attendance(manager_id, site_id, request, current_user)
    logger.info(
        "Attendance recorded: %d new, %d updated, %d failed for site %s",
        result["created_count"], result["updated_count"], result["failed_count"], site_id,
    )
    return result


@router.get("/{manager_id}/sites/{site_id}/attendance")
async def get_site_attendance(
    manager_id: int,
    site_id: int,
    attendance_date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get attendance records for a site. Optionally filter by date."""
    return await service.get_attendance(manager_id, site_id, attendance_date, current_user)
