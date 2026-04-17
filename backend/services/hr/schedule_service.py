"""Service layer for employee schedule management."""

import logging
from datetime import date, timedelta
from typing import Any, Optional

from pymongo.errors import DuplicateKeyError

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ScheduleService(BaseService):
    """Business logic for creating, assigning, and swapping schedules."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    async def create_schedule(self, payload: Any):
        """
        Create schedule(s), supporting single or date-range bulk mode.

        Validations:
        - start_date/end_date must be valid ISO dates
        - employee_ids must be provided for bulk mode

        Args:
            payload: Schedule payload (`employee_id/work_date` for single or
                     `employee_ids/start_date/end_date` for bulk)

        Returns:
            Created schedule or bulk summary
        """
        from backend.models import Schedule

        data = self._to_dict(payload)
        if "employee_ids" in data:
            try:
                start = date.fromisoformat(data["start_date"])
                end = date.fromisoformat(data["end_date"])
            except (ValueError, KeyError):
                self.raise_bad_request("Invalid date format. Please use YYYY-MM-DD.")

            success_count = 0
            skipped_count = 0
            for i in range((end - start).days + 1):
                work_date = (start + timedelta(days=i)).isoformat()
                for emp_id in data.get("employee_ids", []):
                    try:
                        schedule = Schedule(
                            uid=await self.get_next_uid("schedules"),
                            employee_uid=emp_id,
                            site_uid=data.get("site_id"),
                            work_date=work_date,
                            task=data.get("task", ""),
                            shift_type=data.get("shift_type"),
                        )
                        await schedule.insert()
                        success_count += 1
                    except DuplicateKeyError:
                        skipped_count += 1

            logger.info("Bulk schedules created=%s skipped=%s", success_count, skipped_count)
            return {
                "status": "success",
                "created_count": success_count,
                "skipped_count": skipped_count,
            }

        schedule = Schedule(
            uid=await self.get_next_uid("schedules"),
            employee_uid=data.get("employee_uid") or data.get("employee_id"),
            site_uid=data.get("site_uid") or data.get("site_id"),
            work_date=data.get("work_date"),
            task=data.get("task", ""),
            shift_type=data.get("shift_type"),
        )
        await schedule.insert()
        logger.info("Schedule created: ID %s", schedule.uid)
        return schedule

    async def assign_schedule_to_employee(self, schedule_id: int, employee_id: int):
        """
        Assign an existing schedule to an employee.

        Args:
            schedule_id: Schedule UID
            employee_id: Employee UID

        Returns:
            Updated schedule document
        """
        from backend.models import Employee, Schedule

        schedule = await Schedule.find_one(Schedule.uid == schedule_id)
        if not schedule:
            self.raise_not_found("Schedule not found")

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")

        schedule.employee_uid = employee_id
        await schedule.save()
        logger.info("Schedule assignment updated")
        return schedule

    async def swap_shifts(self, first_schedule_id: int, second_schedule_id: int) -> dict:
        """
        Swap shift type and employee assignment between two schedules.

        Validations:
        - Both schedules must exist

        Args:
            first_schedule_id: First schedule UID
            second_schedule_id: Second schedule UID

        Returns:
            Swap operation summary
        """
        from backend.models import Schedule

        first = await Schedule.find_one(Schedule.uid == first_schedule_id)
        second = await Schedule.find_one(Schedule.uid == second_schedule_id)
        if not first or not second:
            self.raise_not_found("One or both schedules not found")

        first.employee_uid, second.employee_uid = second.employee_uid, first.employee_uid
        first.shift_type, second.shift_type = second.shift_type, first.shift_type
        await first.save()
        await second.save()

        logger.info("Shifts swapped between schedules %s and %s", first_schedule_id, second_schedule_id)
        return {
            "message": "Shifts swapped successfully",
            "first_schedule_id": first_schedule_id,
            "second_schedule_id": second_schedule_id,
        }

    async def get_schedule_by_id(self, schedule_id: int):
        from backend.models import Schedule

        schedule = await Schedule.find_one(Schedule.uid == schedule_id)
        if not schedule:
            self.raise_not_found(f"Schedule {schedule_id} not found")
        return schedule

    async def get_all_schedules(self):
        from backend.models import Schedule

        return await Schedule.find_all().sort("+uid").to_list()

    async def update_schedule(self, schedule_id: int, payload: Any):
        schedule = await self.get_schedule_by_id(schedule_id)
        data = self._to_dict(payload)
        for field, value in data.items():
            setattr(schedule, field, value)
        await schedule.save()
        return schedule

    async def delete_schedule(self, schedule_id: int) -> bool:
        schedule = await self.get_schedule_by_id(schedule_id)
        await schedule.delete()
        return True
