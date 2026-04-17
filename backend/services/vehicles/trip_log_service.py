"""Service layer for trip log operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class TripLogService(BaseService):
    """Trip log CRUD and reporting operations."""

    async def create_trip_log(self, payload: Any):
        from backend.models import TripLog

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("trip_logs")
        trip_log = TripLog(**data)
        await trip_log.insert()
        return trip_log

    async def get_trip_log_by_id(self, trip_log_id: int):
        from backend.models import TripLog

        trip_log = await TripLog.find_one(TripLog.uid == trip_log_id)
        if not trip_log:
            self.raise_not_found(f"Trip log {trip_log_id} not found")
        return trip_log

    async def get_trip_logs_for_vehicle(self, vehicle_id: int):
        from backend.models import TripLog

        return await TripLog.find(TripLog.vehicle_id == vehicle_id).sort("-trip_date").to_list()

    async def update_trip_log(self, trip_log_id: int, payload: Any):
        trip_log = await self.get_trip_log_by_id(trip_log_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(trip_log, field, value)
        await trip_log.save()
        return trip_log

    async def delete_trip_log(self, trip_log_id: int) -> bool:
        trip_log = await self.get_trip_log_by_id(trip_log_id)
        await trip_log.delete()
        return True
