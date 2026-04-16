import logging
from datetime import datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.models import Admin, ManagerAttendanceConfig, ManagerAttendance
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/managers/attendance",
    tags=["Manager Attendance"],
    dependencies=[Depends(get_current_active_user)]
)
logger = setup_logger("ManagerAttendanceRouter", log_file="logs/manager_attendance.log", level=logging.DEBUG)

# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class OverrideAttendanceRequest(BaseModel):
    manager_id: int
    date: str  # YYYY-MM-DD
    segment: str  # "morning" | "afternoon" | "evening"
    status: str  # "Admin Override" | "On Time" | "Late" | "Absent" | "Leave"
    check_in_time: Optional[str] = None  # HH:MM (24-hour format)
    reason: str


class SegmentConfig(BaseModel):
    enabled: Optional[bool] = None
    start_time: Optional[str] = None  # HH:MM
    end_time: Optional[str] = None    # HH:MM


class UpdateAttendanceConfigRequest(BaseModel):
    require_all_segments: Optional[bool] = None
    morning: Optional[SegmentConfig] = None
    afternoon: Optional[SegmentConfig] = None
    evening: Optional[SegmentConfig] = None

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_check_in_field(segment: str) -> str:
    """Return the model field name for a segment's check-in timestamp."""
    if segment == "evening":
        return "evening_check_out"
    return f"{segment}_check_in"


def _parse_time_str(t: str) -> time:
    """Parse a time string in 'HH:MM' or 'HH:MM:SS' format to a time object."""
    try:
        parts = t.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError, AttributeError):
        raise ValueError(f"Invalid time format '{t}'. Expected 'HH:MM' or 'HH:MM:SS'.")


def calculate_day_status(attendance: ManagerAttendance, config: ManagerAttendanceConfig) -> str:
    """Calculate overall day status based on segment statuses."""
    enabled_segments = []
    if config.morning_enabled:
        enabled_segments.append("morning")
    if config.afternoon_enabled:
        enabled_segments.append("afternoon")
    if config.evening_enabled:
        enabled_segments.append("evening")

    completed_segments = 0
    for segment in enabled_segments:
        seg_status = getattr(attendance, f"{segment}_status")
        if seg_status in ["On Time", "Late", "Admin Override"]:
            completed_segments += 1

    total_enabled = len(enabled_segments)

    if total_enabled == 0:
        return "Pending"
    elif completed_segments == 0:
        return "Pending"
    elif completed_segments == total_enabled:
        return "Full Day"
    else:
        return "Partial"

# =============================================================================
# MANAGER SELF-SERVICE ENDPOINTS
# =============================================================================

@router.get("/my-config")
async def get_my_attendance_config(
    current_user: dict = Depends(get_current_active_user)
):
    """Get my attendance configuration (time windows). Manager only."""
    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me or me.role != "Site Manager":
        raise HTTPException(403, "Only Site Managers can access this endpoint")

    config = await ManagerAttendanceConfig.find_one(
        ManagerAttendanceConfig.manager_id == me.uid
    )

    if not config:
        config = ManagerAttendanceConfig(
            uid=await get_next_uid("manager_attendance_configs"),
            manager_id=me.uid,
            configured_by_admin_id=1
        )
        await config.insert()

    return {
        "manager_id": me.uid,
        "morning_enabled": config.morning_enabled,
        "morning_window_start": config.morning_window_start if config.morning_enabled else None,
        "morning_window_end": config.morning_window_end if config.morning_enabled else None,
        "afternoon_enabled": config.afternoon_enabled,
        "afternoon_window_start": config.afternoon_window_start if config.afternoon_enabled else None,
        "afternoon_window_end": config.afternoon_window_end if config.afternoon_enabled else None,
        "evening_enabled": config.evening_enabled,
        "evening_window_start": config.evening_window_start if config.evening_enabled else None,
        "evening_window_end": config.evening_window_end if config.evening_enabled else None,
        "require_all_segments": config.require_all_segments
    }


@router.post("/check-in/{segment}")
async def manager_check_in(
    segment: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Manager checks in for a specific segment (morning/afternoon/evening).

    Validates:
    - Current time is within configured window
    - Segment is enabled
    - Not already checked in

    Manager only.
    """
    if segment not in ["morning", "afternoon", "evening"]:
        raise HTTPException(400, "Invalid segment. Must be 'morning', 'afternoon', or 'evening'")

    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me or me.role != "Site Manager":
        raise HTTPException(403, "Only Site Managers can check in")

    config = await ManagerAttendanceConfig.find_one(
        ManagerAttendanceConfig.manager_id == me.uid
    )
    if not config:
        raise HTTPException(404, "Attendance configuration not found")

    segment_enabled = getattr(config, f"{segment}_enabled")
    if not segment_enabled:
        raise HTTPException(400, f"{segment.capitalize()} check-in is disabled for your account")

    window_start = getattr(config, f"{segment}_window_start")
    window_end = getattr(config, f"{segment}_window_end")

    now = datetime.now()
    current_time = now.time()
    current_date = now.date()

    # Parse window strings ("HH:MM") to time objects for comparison
    window_start_time = _parse_time_str(window_start)
    window_end_time = _parse_time_str(window_end)

    if not (window_start_time <= current_time <= window_end_time):
        raise HTTPException(
            400,
            f"Check-in window closed. {segment.capitalize()} window: "
            f"{window_start_time.strftime('%H:%M')} - {window_end_time.strftime('%H:%M')}"
        )

    attendance = await ManagerAttendance.find_one(
        ManagerAttendance.manager_id == me.uid,
        ManagerAttendance.date == current_date
    )

    if not attendance:
        attendance = ManagerAttendance(
            uid=await get_next_uid("manager_attendance"),
            manager_id=me.uid,
            date=current_date
        )

    check_in_field = get_check_in_field(segment)
    existing_check_in = getattr(attendance, check_in_field)
    if existing_check_in:
        raise HTTPException(
            400,
            f"Already checked in for {segment} at {existing_check_in.strftime('%H:%M')}"
        )

    setattr(attendance, check_in_field, now)

    grace_period = timedelta(minutes=10)
    grace_end = (datetime.combine(current_date, window_start_time) + grace_period).time()

    if current_time <= grace_end:
        status = "On Time"
    else:
        status = "Late"

    setattr(attendance, f"{segment}_status", status)

    attendance.day_status = calculate_day_status(attendance, config)
    attendance.updated_at = datetime.now()

    await attendance.save()

    logger.info(
        f"Manager {me.uid} checked in for {segment} at {now.strftime('%H:%M')} - Status: {status}"
    )

    return {
        "message": f"{segment.capitalize()} check-in successful",
        "check_in_time": now.isoformat(),
        "status": status,
        "day_status": attendance.day_status
    }


@router.get("/my-today")
async def get_my_today_attendance(
    current_user: dict = Depends(get_current_active_user)
):
    """Get my attendance record for today. Manager only."""
    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me or me.role != "Site Manager":
        raise HTTPException(403, "Only Site Managers can access this endpoint")

    today = datetime.now().date()

    attendance = await ManagerAttendance.find_one(
        ManagerAttendance.manager_id == me.uid,
        ManagerAttendance.date == today
    )

    config = await ManagerAttendanceConfig.find_one(
        ManagerAttendanceConfig.manager_id == me.uid
    )

    if not attendance:
        return {
            "date": today.isoformat(),
            "day_status": "Pending",
            "morning_check_in": None,
            "morning_status": None,
            "afternoon_check_in": None,
            "afternoon_status": None,
            "evening_check_in": None,
            "evening_status": None,
            "is_overridden": False
        }

    return {
        "date": attendance.date.isoformat(),
        "day_status": attendance.day_status,
        "morning_check_in": attendance.morning_check_in.isoformat() if attendance.morning_check_in else None,
        "morning_status": attendance.morning_status,
        "afternoon_check_in": attendance.afternoon_check_in.isoformat() if attendance.afternoon_check_in else None,
        "afternoon_status": attendance.afternoon_status,
        "evening_check_in": attendance.evening_check_out.isoformat() if attendance.evening_check_out else None,
        "evening_status": attendance.evening_status,
        "notes": attendance.notes,
        "is_overridden": attendance.is_overridden
    }


@router.get("/my-history")
async def get_my_attendance_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get my attendance history. Manager only.

    Query params:
    - start_date: YYYY-MM-DD (default: first day of current month)
    - end_date: YYYY-MM-DD (default: today)
    """
    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me or me.role != "Site Manager":
        raise HTTPException(403, "Only Site Managers can access this endpoint")

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = datetime.now().date().replace(day=1)

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = datetime.now().date()

    records = await ManagerAttendance.find(
        ManagerAttendance.manager_id == me.uid,
        ManagerAttendance.date >= start,
        ManagerAttendance.date <= end
    ).sort(-ManagerAttendance.date).to_list()

    result = []
    for record in records:
        result.append({
            "date": record.date.isoformat(),
            "day_status": record.day_status,
            "morning_check_in": record.morning_check_in.isoformat() if record.morning_check_in else None,
            "morning_status": record.morning_status,
            "afternoon_check_in": record.afternoon_check_in.isoformat() if record.afternoon_check_in else None,
            "afternoon_status": record.afternoon_status,
            "evening_check_in": record.evening_check_out.isoformat() if record.evening_check_out else None,
            "evening_status": record.evening_status,
            "is_overridden": record.is_overridden
        })

    full_days = len([r for r in records if r.day_status == "Full Day"])
    partial_days = len([r for r in records if r.day_status == "Partial"])
    absent_days = len([r for r in records if r.day_status == "Absent"])

    return {
        "records": result,
        "summary": {
            "total_days": len(records),
            "full_days": full_days,
            "partial_days": partial_days,
            "absent_days": absent_days
        }
    }

# =============================================================================
# ADMIN CONTROL ENDPOINTS
# =============================================================================

@router.get("/all")
async def get_all_managers_attendance(
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get attendance for all managers on a specific date. Admin only.

    Query param:
    - date: YYYY-MM-DD (default: today)
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(403, "Only Admins can access this endpoint")

    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = datetime.now().date()

    managers = await Admin.find(
        {"role": "Site Manager", "is_active": True}
    ).to_list()

    result = []
    for manager in managers:
        attendance = await ManagerAttendance.find_one(
            ManagerAttendance.manager_id == manager.uid,
            ManagerAttendance.date == target_date
        )

        result.append({
            "manager_id": manager.uid,
            "manager_name": manager.full_name,
            "day_status": attendance.day_status if attendance else "Pending",
            "morning": {
                "time": attendance.morning_check_in.strftime('%H:%M') if attendance and attendance.morning_check_in else None,
                "status": attendance.morning_status if attendance else None,
                "key": "morning"
            },
            "afternoon": {
                "time": attendance.afternoon_check_in.strftime('%H:%M') if attendance and attendance.afternoon_check_in else None,
                "status": attendance.afternoon_status if attendance else None,
                "key": "afternoon"
            },
            "evening": {
                "time": attendance.evening_check_out.strftime('%H:%M') if attendance and attendance.evening_check_out else None,
                "status": attendance.evening_status if attendance else None,
                "key": "evening"
            },
        })

    return result


@router.post("/override")
async def override_manager_attendance(
    payload: OverrideAttendanceRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Override a manager's attendance segment. Admin only."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(403, "Only Admins can override attendance")

    if payload.segment not in ["morning", "afternoon", "evening"]:
        raise HTTPException(400, "Invalid segment")

    target_date = datetime.strptime(payload.date, "%Y-%m-%d").date()

    attendance = await ManagerAttendance.find_one(
        ManagerAttendance.manager_id == payload.manager_id,
        ManagerAttendance.date == target_date
    )

    if not attendance:
        attendance = ManagerAttendance(
            uid=await get_next_uid("manager_attendance"),
            manager_id=payload.manager_id,
            date=target_date
        )

    if payload.check_in_time:
        check_in_dt = datetime.combine(
            target_date,
            datetime.strptime(payload.check_in_time, "%H:%M").time()
        )
        setattr(attendance, get_check_in_field(payload.segment), check_in_dt)

    setattr(attendance, f"{payload.segment}_status", payload.status)

    attendance.is_overridden = True
    attendance.overridden_by_admin_id = current_user.get("id")
    attendance.override_reason = payload.reason
    attendance.override_timestamp = datetime.now()
    attendance.updated_at = datetime.now()

    config = await ManagerAttendanceConfig.find_one(
        ManagerAttendanceConfig.manager_id == payload.manager_id
    )
    if config:
        attendance.day_status = calculate_day_status(attendance, config)

    await attendance.save()

    logger.info(
        f"Admin {current_user.get('id')} overrode manager {payload.manager_id} "
        f"attendance: {payload.segment} on {target_date}"
    )

    return {"message": "Attendance overridden successfully"}


@router.put("/config/{manager_id}")
async def update_manager_attendance_config(
    manager_id: int,
    payload: UpdateAttendanceConfigRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Update a manager's attendance configuration (time windows). Admin only."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(403, "Only Admins can update attendance configuration")

    config = await ManagerAttendanceConfig.find_one(
        ManagerAttendanceConfig.manager_id == manager_id
    )

    if not config:
        config = ManagerAttendanceConfig(
            uid=await get_next_uid("manager_attendance_configs"),
            manager_id=manager_id,
            configured_by_admin_id=current_user.get("id", 1)
        )

    update_data = payload.dict(exclude_unset=True)
    for segment in ["morning", "afternoon", "evening"]:
        seg_data = update_data.get(segment)
        if seg_data is not None:
            if "enabled" in seg_data:
                setattr(config, f"{segment}_enabled", seg_data["enabled"])
            if "start_time" in seg_data and seg_data["start_time"] is not None:
                setattr(config, f"{segment}_window_start", seg_data["start_time"])
            if "end_time" in seg_data and seg_data["end_time"] is not None:
                setattr(config, f"{segment}_window_end", seg_data["end_time"])
    if "require_all_segments" in update_data:
        config.require_all_segments = update_data["require_all_segments"]

    config.configured_by_admin_id = current_user.get("id", 1)
    config.updated_at = datetime.now()

    await config.save()

    logger.info(
        f"Admin {current_user.get('id')} updated attendance config for manager {manager_id}"
    )

    return {"message": "Attendance configuration updated successfully"}


@router.get("/config/{manager_id}")
async def get_manager_attendance_config(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get a manager's attendance configuration. Admin only."""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(403, "Only Admins can view attendance configuration")

    config = await ManagerAttendanceConfig.find_one(
        ManagerAttendanceConfig.manager_id == manager_id
    )

    if not config:
        return {
            "manager_id": manager_id,
            "require_all_segments": True,
            "morning": {"enabled": True, "start_time": "08:00", "end_time": "09:30"},
            "afternoon": {"enabled": True, "start_time": "13:00", "end_time": "14:00"},
            "evening": {"enabled": True, "start_time": "17:00", "end_time": "18:30"},
        }

    return {
        "manager_id": manager_id,
        "require_all_segments": config.require_all_segments,
        "morning": {
            "enabled": config.morning_enabled,
            "start_time": config.morning_window_start,
            "end_time": config.morning_window_end,
        },
        "afternoon": {
            "enabled": config.afternoon_enabled,
            "start_time": config.afternoon_window_start,
            "end_time": config.afternoon_window_end,
        },
        "evening": {
            "enabled": config.evening_enabled,
            "start_time": config.evening_window_start,
            "end_time": config.evening_window_end,
        },
        "configured_by": config.configured_by_admin_id,
        "last_updated": config.updated_at.isoformat()
    }
