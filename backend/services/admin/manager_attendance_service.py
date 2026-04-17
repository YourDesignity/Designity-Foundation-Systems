"""Service layer for manager attendance records."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class ManagerAttendanceService(BaseService):
    """Manager attendance and summary operations."""

    async def create_attendance_record(self, payload: Any):
        from backend.models import ManagerAttendance

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("manager_attendance")
        record = ManagerAttendance(**data)
        await record.insert()
        return record

    async def get_attendance_record(self, record_id: int):
        from backend.models import ManagerAttendance

        record = await ManagerAttendance.find_one(ManagerAttendance.uid == record_id)
        if not record:
            self.raise_not_found(f"Manager attendance {record_id} not found")
        return record

    async def get_attendance_by_manager(self, manager_id: int):
        from backend.models import ManagerAttendance

        return await ManagerAttendance.find(ManagerAttendance.manager_id == manager_id).sort("-date").to_list()

    async def update_attendance_record(self, record_id: int, payload: Any):
        record = await self.get_attendance_record(record_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(record, field, value)
        await record.save()
        return record

    async def get_or_create_config(self, manager_id: int):
        from backend.models import ManagerAttendanceConfig

        config = await ManagerAttendanceConfig.find_one(ManagerAttendanceConfig.manager_id == manager_id)
        if config:
            return config

        config = ManagerAttendanceConfig(uid=await get_next_uid("manager_attendance_configs"), manager_id=manager_id)
        await config.insert()
        return config
