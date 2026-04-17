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
