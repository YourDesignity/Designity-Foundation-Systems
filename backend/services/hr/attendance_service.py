"""Service layer for employee attendance tracking."""

from datetime import date
from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class AttendanceService(BaseService):
    """Employee attendance tracking and reporting operations."""

    async def mark_attendance(self, payload: Any):
        from backend.models import Attendance

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        work_date = self.coerce_datetime(data.get("date")) if data.get("date") else None
        if work_date and work_date.date() > date.today():
            self.raise_bad_request("Cannot mark attendance for future dates")

        data["uid"] = await get_next_uid("attendance")
        attendance = Attendance(**data)
        await attendance.insert()
        return attendance

    async def get_attendance_by_id(self, attendance_id: int):
        from backend.models import Attendance

        record = await Attendance.find_one(Attendance.uid == attendance_id)
        if not record:
            self.raise_not_found(f"Attendance {attendance_id} not found")
        return record

    async def get_attendance_for_employee(self, employee_id: int):
        from backend.models import Attendance

        return await Attendance.find(Attendance.employee_id == employee_id).sort("-date").to_list()

    async def update_attendance(self, attendance_id: int, payload: Any):
        record = await self.get_attendance_by_id(attendance_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(record, field, value)
        await record.save()
        return record

    async def delete_attendance(self, attendance_id: int) -> bool:
        record = await self.get_attendance_by_id(attendance_id)
        await record.delete()
        return True
