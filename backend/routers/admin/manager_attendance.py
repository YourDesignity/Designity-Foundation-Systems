import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.admin.manager_attendance_service import ManagerAttendanceService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/managers/attendance",
    tags=["Manager Attendance"],
    dependencies=[Depends(get_current_active_user)],
)
logger = setup_logger("ManagerAttendanceRouter", log_file="logs/manager_attendance.log", level=logging.DEBUG)
service = ManagerAttendanceService()


class OverrideAttendanceRequest(BaseModel):
    manager_id: int
    date: str
    segment: str
    status: str
    check_in_time: Optional[str] = None
    reason: str


class SegmentConfig(BaseModel):
    enabled: Optional[bool] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class UpdateAttendanceConfigRequest(BaseModel):
    require_all_segments: Optional[bool] = None
    morning: Optional[SegmentConfig] = None
    afternoon: Optional[SegmentConfig] = None
    evening: Optional[SegmentConfig] = None


@router.get("/my-config")
async def get_my_attendance_config(current_user: dict = Depends(get_current_active_user)):
    return await service.get_my_attendance_config(current_user)


@router.post("/check-in/{segment}")
async def manager_check_in(
    segment: str,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.manager_check_in(segment, current_user)


@router.get("/my-today")
async def get_my_today_attendance(current_user: dict = Depends(get_current_active_user)):
    return await service.get_my_today_attendance(current_user)


@router.get("/my-history")
async def get_my_attendance_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.get_my_attendance_history(current_user, start_date, end_date)


@router.get("/all")
async def get_all_managers_attendance(
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.get_all_managers_attendance(current_user, date)


@router.post("/override")
async def override_manager_attendance(
    payload: OverrideAttendanceRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.override_manager_attendance(payload, current_user)


@router.put("/config/{manager_id}")
async def update_manager_attendance_config(
    manager_id: int,
    payload: UpdateAttendanceConfigRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.update_manager_attendance_config(manager_id, payload, current_user)


@router.get("/config/{manager_id}")
async def get_manager_attendance_config(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.get_manager_attendance_config(manager_id, current_user)
