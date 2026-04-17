"""Service layer for employee schedule management."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class ScheduleService(BaseService):
    """Schedule CRUD and manager filtering operations."""

    async def create_schedule(self, payload: Any):
        from backend.models import Schedule

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("schedules")
        schedule = Schedule(**data)
        await schedule.insert()
        return schedule

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
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(schedule, field, value)
        await schedule.save()
        return schedule

    async def delete_schedule(self, schedule_id: int) -> bool:
        schedule = await self.get_schedule_by_id(schedule_id)
        await schedule.delete()
        return True
