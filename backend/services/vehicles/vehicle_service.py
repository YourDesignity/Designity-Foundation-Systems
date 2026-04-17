"""Service layer for vehicle operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class VehicleService(BaseService):
    """Vehicle CRUD and lifecycle operations."""

    async def create_vehicle(self, payload: Any):
        from backend.models import Vehicle

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("vehicles")
        vehicle = Vehicle(**data)
        await vehicle.insert()
        return vehicle

    async def get_vehicle_by_id(self, vehicle_id: int):
        from backend.models import Vehicle

        vehicle = await Vehicle.find_one(Vehicle.uid == vehicle_id)
        if not vehicle:
            self.raise_not_found(f"Vehicle {vehicle_id} not found")
        return vehicle

    async def get_vehicles(self):
        from backend.models import Vehicle

        return await Vehicle.find_all().sort("+uid").to_list()

    async def update_vehicle(self, vehicle_id: int, payload: Any):
        vehicle = await self.get_vehicle_by_id(vehicle_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(vehicle, field, value)
        await vehicle.save()
        return vehicle

    async def delete_vehicle(self, vehicle_id: int) -> bool:
        vehicle = await self.get_vehicle_by_id(vehicle_id)
        await vehicle.delete()
        return True
