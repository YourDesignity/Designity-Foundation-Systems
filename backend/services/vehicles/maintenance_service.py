"""Service layer for maintenance operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class MaintenanceService(BaseService):
    """Vehicle maintenance CRUD and schedule operations."""

    async def create_maintenance_log(self, payload: Any):
        from backend.models import MaintenanceLog

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("maintenance_logs")
        log = MaintenanceLog(**data)
        await log.insert()
        return log

    async def get_maintenance_log_by_id(self, log_id: int):
        from backend.models import MaintenanceLog

        log = await MaintenanceLog.find_one(MaintenanceLog.uid == log_id)
        if not log:
            self.raise_not_found(f"Maintenance log {log_id} not found")
        return log

    async def get_maintenance_logs_for_vehicle(self, vehicle_id: int):
        from backend.models import MaintenanceLog

        return await MaintenanceLog.find(MaintenanceLog.vehicle_id == vehicle_id).sort("-service_date").to_list()

    async def update_maintenance_log(self, log_id: int, payload: Any):
        log = await self.get_maintenance_log_by_id(log_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(log, field, value)
        await log.save()
        return log

    async def delete_maintenance_log(self, log_id: int) -> bool:
        log = await self.get_maintenance_log_by_id(log_id)
        await log.delete()
        return True
