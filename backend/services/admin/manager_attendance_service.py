"""Service layer for manager attendance operations."""

import logging
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ManagerAttendanceService(BaseService):
    """Business logic for manager check-in/check-out and monthly summaries."""

    @staticmethod
    def _parse_time_str(value: str) -> time:
        try:
            parts = value.split(":")
            return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError, AttributeError) as exc:
            raise ValueError(f"Invalid time format '{value}'. Expected HH:MM.") from exc

    @staticmethod
    def _get_check_in_field(segment: str) -> str:
        return "evening_check_out" if segment == "evening" else f"{segment}_check_in"

    @staticmethod
    def _calculate_day_status(attendance: Any, config: Any) -> str:
        enabled_segments = []
        if config.morning_enabled:
            enabled_segments.append("morning")
        if config.afternoon_enabled:
            enabled_segments.append("afternoon")
        if config.evening_enabled:
            enabled_segments.append("evening")

        completed = 0
        for segment in enabled_segments:
            seg_status = getattr(attendance, f"{segment}_status")
            if seg_status in ["On Time", "Late", "Admin Override"]:
                completed += 1

        if not enabled_segments or completed == 0:
            return "Pending"
        if completed == len(enabled_segments):
            return "Full Day"
        return "Partial"

    async def _get_or_create_config(self, manager_id: int, configured_by: int = 1):
        from backend.models import ManagerAttendanceConfig

        config = await ManagerAttendanceConfig.find_one(ManagerAttendanceConfig.manager_id == manager_id)
        if config:
            return config

        config = ManagerAttendanceConfig(
            uid=await self.get_next_uid("manager_attendance_configs"),
            manager_id=manager_id,
            configured_by_admin_id=configured_by,
        )
        await config.insert()
        return config

    async def record_check_in(
        self,
        manager_id: int,
        segment: str,
        check_time: Optional[datetime] = None,
    ) -> dict:
        """
        Record manager check-in/check-out by segment.

        Validations:
        - Segment must be morning/afternoon/evening
        - Segment must be enabled in manager config
        - Check-in must be inside configured window
        - Segment must not already be recorded for the day

        Args:
            manager_id: Manager UID
            segment: Segment name
            check_time: Optional timestamp override

        Returns:
            Attendance result payload

        Raises:
            HTTPException 400/404: Validation and lookup failures
        """
        from backend.models import ManagerAttendance

        if segment not in {"morning", "afternoon", "evening"}:
            self.raise_bad_request("Invalid segment. Must be 'morning', 'afternoon', or 'evening'")

        now = check_time or datetime.now()
        current_date = now.date()
        current_time = now.time()

        config = await self._get_or_create_config(manager_id)
        if not getattr(config, f"{segment}_enabled"):
            self.raise_bad_request(f"{segment.capitalize()} check-in is disabled for this manager")

        window_start = self._parse_time_str(getattr(config, f"{segment}_window_start"))
        window_end = self._parse_time_str(getattr(config, f"{segment}_window_end"))
        if not (window_start <= current_time <= window_end):
            self.raise_bad_request(
                f"Check-in window closed. {segment.capitalize()} window: "
                f"{window_start.strftime('%H:%M')} - {window_end.strftime('%H:%M')}"
            )

        attendance = await ManagerAttendance.find_one(
            ManagerAttendance.manager_id == manager_id,
            ManagerAttendance.date == current_date,
        )
        if not attendance:
            attendance = ManagerAttendance(
                uid=await self.get_next_uid("manager_attendance"),
                manager_id=manager_id,
                date=current_date,
            )

        check_field = self._get_check_in_field(segment)
        if getattr(attendance, check_field):
            self.raise_bad_request(f"Already checked in for {segment}")

        setattr(attendance, check_field, now)
        grace_end = (datetime.combine(current_date, window_start) + timedelta(minutes=10)).time()
        setattr(attendance, f"{segment}_status", "On Time" if current_time <= grace_end else "Late")
        attendance.day_status = self._calculate_day_status(attendance, config)
        attendance.updated_at = datetime.now()
        await attendance.save()

        logger.info("Manager %s checked %s at %s", manager_id, segment, now.isoformat())
        return {
            "manager_id": manager_id,
            "segment": segment,
            "check_time": now.isoformat(),
            "segment_status": getattr(attendance, f"{segment}_status"),
            "day_status": attendance.day_status,
        }

    async def record_check_out(self, manager_id: int, check_time: Optional[datetime] = None) -> dict:
        """
        Record evening checkout.

        Args:
            manager_id: Manager UID
            check_time: Optional timestamp override

        Returns:
            Attendance segment payload
        """
        return await self.record_check_in(manager_id=manager_id, segment="evening", check_time=check_time)

    async def get_monthly_attendance(self, manager_id: int, year: int, month: int) -> dict:
        """
        Get manager monthly attendance summary.

        Validations:
        - Month must be 1..12

        Args:
            manager_id: Manager UID
            year: Year
            month: Month number

        Returns:
            Monthly attendance records and summary counts
        """
        from backend.models import ManagerAttendance

        if month < 1 or month > 12:
            self.raise_bad_request("Month must be between 1 and 12")

        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        records = await ManagerAttendance.find(
            ManagerAttendance.manager_id == manager_id,
            ManagerAttendance.date >= start,
            ManagerAttendance.date < end,
        ).sort("-date").to_list()

        serialized = [
            {
                "date": r.date.isoformat(),
                "day_status": r.day_status,
                "morning_status": r.morning_status,
                "afternoon_status": r.afternoon_status,
                "evening_status": r.evening_status,
                "is_overridden": r.is_overridden,
            }
            for r in records
        ]
        return {
            "manager_id": manager_id,
            "year": year,
            "month": month,
            "records": serialized,
            "summary": {
                "total_days": len(records),
                "full_days": len([r for r in records if r.day_status == "Full Day"]),
                "partial_days": len([r for r in records if r.day_status == "Partial"]),
                "absent_days": len([r for r in records if r.day_status == "Absent"]),
            },
        }

    async def get_my_attendance_config(self, current_user: dict) -> dict:
        """Get current manager attendance config."""
        from backend.models import Admin

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.role != "Site Manager":
            self.raise_forbidden("Only Site Managers can access this endpoint")

        config = await self._get_or_create_config(me.uid)
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
            "require_all_segments": config.require_all_segments,
        }

    async def manager_check_in(self, segment: str, current_user: dict) -> dict:
        """Manager self check-in for segment."""
        from backend.models import Admin, ManagerAttendanceConfig

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.role != "Site Manager":
            self.raise_forbidden("Only Site Managers can check in")

        config = await ManagerAttendanceConfig.find_one(ManagerAttendanceConfig.manager_id == me.uid)
        if not config:
            self.raise_not_found("Attendance configuration not found")

        result = await self.record_check_in(manager_id=me.uid, segment=segment)
        return {
            "message": f"{segment.capitalize()} check-in successful",
            "check_in_time": result["check_time"],
            "status": result["segment_status"],
            "day_status": result["day_status"],
        }

    async def get_my_today_attendance(self, current_user: dict) -> dict:
        """Get current manager's today attendance."""
        from backend.models import Admin, ManagerAttendance

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.role != "Site Manager":
            self.raise_forbidden("Only Site Managers can access this endpoint")

        today = datetime.now().date()
        attendance = await ManagerAttendance.find_one(
            ManagerAttendance.manager_id == me.uid,
            ManagerAttendance.date == today,
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
                "is_overridden": False,
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
            "is_overridden": attendance.is_overridden,
        }

    async def get_my_attendance_history(
        self,
        current_user: dict,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """Get manager self attendance history."""
        from backend.models import Admin, ManagerAttendance

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.role != "Site Manager":
            self.raise_forbidden("Only Site Managers can access this endpoint")

        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else datetime.now().date().replace(day=1)
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.now().date()

        records = await ManagerAttendance.find(
            ManagerAttendance.manager_id == me.uid,
            ManagerAttendance.date >= start,
            ManagerAttendance.date <= end,
        ).sort(-ManagerAttendance.date).to_list()

        result = [
            {
                "date": record.date.isoformat(),
                "day_status": record.day_status,
                "morning_check_in": record.morning_check_in.isoformat() if record.morning_check_in else None,
                "morning_status": record.morning_status,
                "afternoon_check_in": record.afternoon_check_in.isoformat() if record.afternoon_check_in else None,
                "afternoon_status": record.afternoon_status,
                "evening_check_in": record.evening_check_out.isoformat() if record.evening_check_out else None,
                "evening_status": record.evening_status,
                "is_overridden": record.is_overridden,
            }
            for record in records
        ]

        return {
            "records": result,
            "summary": {
                "total_days": len(records),
                "full_days": len([r for r in records if r.day_status == "Full Day"]),
                "partial_days": len([r for r in records if r.day_status == "Partial"]),
                "absent_days": len([r for r in records if r.day_status == "Absent"]),
            },
        }

    async def get_all_managers_attendance(self, current_user: dict, date_str: Optional[str] = None) -> list[dict]:
        """Get all managers attendance for a target date."""
        from backend.models import Admin, ManagerAttendance

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can access this endpoint")

        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        managers = await Admin.find({"role": "Site Manager", "is_active": True}).to_list()

        result = []
        for manager in managers:
            attendance = await ManagerAttendance.find_one(
                ManagerAttendance.manager_id == manager.uid,
                ManagerAttendance.date == target_date,
            )
            result.append(
                {
                    "manager_id": manager.uid,
                    "manager_name": manager.full_name,
                    "day_status": attendance.day_status if attendance else "Pending",
                    "morning": {
                        "time": attendance.morning_check_in.strftime("%H:%M") if attendance and attendance.morning_check_in else None,
                        "status": attendance.morning_status if attendance else None,
                        "key": "morning",
                    },
                    "afternoon": {
                        "time": attendance.afternoon_check_in.strftime("%H:%M")
                        if attendance and attendance.afternoon_check_in
                        else None,
                        "status": attendance.afternoon_status if attendance else None,
                        "key": "afternoon",
                    },
                    "evening": {
                        "time": attendance.evening_check_out.strftime("%H:%M") if attendance and attendance.evening_check_out else None,
                        "status": attendance.evening_status if attendance else None,
                        "key": "evening",
                    },
                }
            )
        return result

    async def override_manager_attendance(self, payload: Any, current_user: dict) -> dict:
        """Override one manager attendance segment."""
        from backend.models import ManagerAttendance, ManagerAttendanceConfig

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can override attendance")

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        segment = data.get("segment")
        if segment not in ["morning", "afternoon", "evening"]:
            self.raise_bad_request("Invalid segment")

        target_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        attendance = await ManagerAttendance.find_one(
            ManagerAttendance.manager_id == data["manager_id"],
            ManagerAttendance.date == target_date,
        )
        if not attendance:
            attendance = ManagerAttendance(
                uid=await self.get_next_uid("manager_attendance"),
                manager_id=data["manager_id"],
                date=target_date,
            )

        check_in_time = data.get("check_in_time")
        if check_in_time:
            check_in_dt = datetime.combine(target_date, datetime.strptime(check_in_time, "%H:%M").time())
            setattr(attendance, self._get_check_in_field(segment), check_in_dt)

        setattr(attendance, f"{segment}_status", data["status"])
        attendance.is_overridden = True
        attendance.overridden_by_admin_id = current_user.get("id")
        attendance.override_reason = data["reason"]
        attendance.override_timestamp = datetime.now()
        attendance.updated_at = datetime.now()

        config = await ManagerAttendanceConfig.find_one(ManagerAttendanceConfig.manager_id == data["manager_id"])
        if config:
            attendance.day_status = self._calculate_day_status(attendance, config)

        await attendance.save()
        return {"message": "Attendance overridden successfully"}

    async def update_manager_attendance_config(self, manager_id: int, payload: Any, current_user: dict) -> dict:
        """Update manager attendance config."""
        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can update attendance configuration")

        config = await self._get_or_create_config(manager_id, configured_by=current_user.get("id", 1))
        update_data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

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
        return {"message": "Attendance configuration updated successfully"}

    async def get_manager_attendance_config(self, manager_id: int, current_user: dict) -> dict:
        """Get manager attendance config for admins."""
        from backend.models import ManagerAttendanceConfig

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can view attendance configuration")

        config = await ManagerAttendanceConfig.find_one(ManagerAttendanceConfig.manager_id == manager_id)
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
            "last_updated": config.updated_at.isoformat(),
        }
