"""Service layer for employee attendance operations."""

import calendar
import logging
from datetime import date
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class AttendanceService(BaseService):
    """Business logic for attendance write/read and monthly calculations."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    async def mark_attendance(self, payload: Any):
        """
        Upsert attendance record(s).

        Validations:
        - Dates cannot be in the future
        - employee_uid is required for each row

        Args:
            payload: Either a single attendance payload or batch payload with `records`

        Returns:
            Operation summary containing created/updated counts
        """
        from backend.models import Attendance

        data = self._to_dict(payload)
        records = data.get("records")
        if records is None:
            records = [data]

        created = 0
        updated = 0
        output = []

        for record in records:
            employee_uid = record.get("employee_uid", record.get("employee_id"))
            if employee_uid is None:
                self.raise_bad_request("employee_uid is required")

            work_date = record.get("date")
            if not work_date:
                self.raise_bad_request("date is required")

            try:
                parsed_work_date = date.fromisoformat(work_date)
            except ValueError:
                self.raise_bad_request("Invalid date format. Please use YYYY-MM-DD.")

            if parsed_work_date > date.today():
                self.raise_bad_request("Cannot mark attendance for future dates")

            site_uid = record.get("site_uid")
            existing_filters = [
                Attendance.employee_uid == employee_uid,
                Attendance.date == work_date,
            ]
            if site_uid is not None:
                existing_filters.append(Attendance.site_uid == site_uid)
            existing = await Attendance.find_one(*existing_filters)
            if existing:
                existing.status = record.get("status", existing.status)
                existing.shift = record.get("shift", existing.shift)
                existing.overtime_hours = record.get("overtime_hours", existing.overtime_hours or 0)
                existing.recorded_by_manager_id = record.get("recorded_by_manager_id", existing.recorded_by_manager_id)
                existing.recorded_by_manager_name = record.get("recorded_by_manager_name", existing.recorded_by_manager_name)
                existing.is_substitute = record.get("is_substitute", existing.is_substitute)
                existing.leave_type = record.get("leave_type", existing.leave_type)
                existing.leave_reason = record.get("leave_reason", existing.leave_reason)
                existing.notes = record.get("notes", existing.notes)
                await existing.save()
                updated += 1
                output.append(existing.model_dump(mode="json"))
            else:
                new_record = Attendance(
                    uid=await self.get_next_uid("attendance"),
                    employee_uid=employee_uid,
                    site_uid=site_uid,
                    date=work_date,
                    status=record.get("status", "Present"),
                    shift=record.get("shift", "Morning"),
                    overtime_hours=record.get("overtime_hours", 0),
                    recorded_by_manager_id=record.get("recorded_by_manager_id"),
                    recorded_by_manager_name=record.get("recorded_by_manager_name"),
                    is_substitute=record.get("is_substitute", False),
                    leave_type=record.get("leave_type"),
                    leave_reason=record.get("leave_reason"),
                    notes=record.get("notes"),
                )
                await new_record.insert()
                created += 1
                output.append(new_record.model_dump(mode="json"))

        logger.info("Attendance marked: created=%s updated=%s", created, updated)
        return {"created": created, "updated": updated, "records": output}

    async def calculate_monthly_attendance(self, year: int, month: int, employee_id: Optional[int] = None) -> dict:
        """
        Calculate monthly attendance summary.

        Args:
            year: Year
            month: Month (1-12)
            employee_id: Optional employee filter

        Returns:
            Monthly summary with status counters
        """
        from backend.models import Attendance

        if not (1 <= month <= 12):
            self.raise_bad_request("Month must be between 1 and 12")

        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        filters = [Attendance.date >= start_date, Attendance.date <= end_date]
        if employee_id is not None:
            filters.append(Attendance.employee_uid == employee_id)

        records = await Attendance.find(*filters).to_list()

        by_status: dict[str, int] = {}
        overtime_total = 0
        for record in records:
            by_status[record.status] = by_status.get(record.status, 0) + 1
            overtime_total += int(record.overtime_hours or 0)

        return {
            "year": year,
            "month": month,
            "employee_id": employee_id,
            "total_records": len(records),
            "by_status": by_status,
            "total_overtime_hours": overtime_total,
        }

    async def get_absent_employees(self, attendance_date: str, site_id: Optional[int] = None) -> list[dict]:
        """
        Get employees marked absent for a date.

        Args:
            attendance_date: Date in YYYY-MM-DD
            site_id: Optional site filter

        Returns:
            List of absent employee summaries
        """
        from backend.models import Attendance, Employee

        filters = [Attendance.date == attendance_date, Attendance.status == "Absent"]
        if site_id is not None:
            filters.append(Attendance.site_uid == site_id)

        records = await Attendance.find(*filters).to_list()
        results: list[dict] = []
        for record in records:
            employee = await Employee.find_one(Employee.uid == record.employee_uid)
            results.append(
                {
                    "employee_id": record.employee_uid,
                    "employee_name": employee.name if employee else None,
                    "date": record.date,
                    "site_id": record.site_uid,
                    "shift": record.shift,
                    "leave_type": record.leave_type,
                    "leave_reason": record.leave_reason,
                }
            )
        return results

    async def get_attendance_by_id(self, attendance_id: int):
        from backend.models import Attendance

        record = await Attendance.find_one(Attendance.uid == attendance_id)
        if not record:
            self.raise_not_found(f"Attendance {attendance_id} not found")
        return record

    async def get_attendance_for_employee(self, employee_id: int):
        from backend.models import Attendance

        return await Attendance.find(Attendance.employee_uid == employee_id).sort("-date").to_list()

    async def update_attendance(self, attendance_id: int, payload: Any):
        record = await self.get_attendance_by_id(attendance_id)
        data = self._to_dict(payload)
        for field, value in data.items():
            setattr(record, field, value)
        await record.save()
        return record

    async def delete_attendance(self, attendance_id: int) -> bool:
        record = await self.get_attendance_by_id(attendance_id)
        await record.delete()
        return True
