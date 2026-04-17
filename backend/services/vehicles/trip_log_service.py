"""Service layer for trip log operations."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class TripLogService(BaseService):
    """Vehicle trip lifecycle and analytics."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _in_window(value: datetime, start_date: Optional[date], end_date: Optional[date]) -> bool:
        if start_date and value.date() < start_date:
            return False
        if end_date and value.date() > end_date:
            return False
        return True

    # ====================================================================
    # CRUD / TRIP LIFECYCLE
    # ====================================================================

    async def start_trip(
        self,
        vehicle_id: int,
        driver_name: str,
        purpose: str,
        start_condition: str = "Good",
        out_time: Optional[datetime] = None,
    ):
        """Start an in-progress trip and lock vehicle status."""
        from backend.models import TripLog, Vehicle

        vehicle = await Vehicle.find_one(Vehicle.uid == vehicle_id)
        if not vehicle:
            self.raise_not_found("Vehicle not found")
        if vehicle.status == "On Trip":
            self.raise_bad_request("Vehicle already has an ongoing trip")

        vehicle.status = "On Trip"
        vehicle.updated_at = datetime.now()
        await vehicle.save()

        uid = await self.get_next_uid("vehicle_trips")
        trip = TripLog(
            uid=uid,
            vehicle_uid=vehicle.uid,
            vehicle_plate=vehicle.plate,
            driver_name=driver_name,
            purpose=purpose,
            start_condition=start_condition,
            out_time=out_time or datetime.now(),
            status="Ongoing",
            start_mileage=vehicle.current_mileage,
        )
        await trip.insert()

        logger.info("Trip started: %s vehicle=%s", uid, vehicle.plate)
        return trip

    async def end_trip(
        self,
        trip_id: int,
        end_mileage: float,
        end_condition: str,
        in_time: Optional[datetime] = None,
    ):
        """Complete an ongoing trip and unlock vehicle status."""
        from backend.models import TripLog, Vehicle

        trip = await self.get_trip_by_id(trip_id)
        if trip.status == "Completed":
            self.raise_bad_request("Trip already completed")
        if end_mileage < trip.start_mileage:
            self.raise_bad_request("End mileage cannot be lower than start mileage")

        trip.in_time = in_time or datetime.now()
        trip.status = "Completed"
        trip.end_mileage = end_mileage
        trip.end_condition = end_condition
        trip.updated_at = datetime.now()
        await trip.save()

        vehicle = await Vehicle.find_one(Vehicle.uid == trip.vehicle_uid)
        if vehicle:
            vehicle.status = "Available"
            vehicle.current_mileage = max(vehicle.current_mileage, end_mileage)
            vehicle.updated_at = datetime.now()
            await vehicle.save()

        logger.info("Trip ended: %s distance=%.2f", trip_id, trip.end_mileage - trip.start_mileage)
        return trip

    async def record_trip(
        self,
        vehicle_id: int,
        driver_name: str,
        purpose: str,
        start_mileage: float,
        end_mileage: float,
        out_time: Optional[datetime] = None,
        in_time: Optional[datetime] = None,
        start_condition: str = "Good",
        end_condition: str = "Good",
    ):
        """Create a completed trip in one operation."""
        if end_mileage < start_mileage:
            self.raise_bad_request("end_mileage must be greater than or equal to start_mileage")

        trip = await self.start_trip(
            vehicle_id=vehicle_id,
            driver_name=driver_name,
            purpose=purpose,
            start_condition=start_condition,
            out_time=out_time,
        )
        trip.start_mileage = start_mileage
        await trip.save()

        return await self.end_trip(
            trip_id=trip.uid,
            end_mileage=end_mileage,
            end_condition=end_condition,
            in_time=in_time,
        )

    async def get_trip_by_id(self, trip_id: int):
        """Get trip by UID."""
        from backend.models import TripLog

        trip = await TripLog.find_one(TripLog.uid == trip_id)
        if not trip:
            self.raise_not_found("Trip not found")
        return trip

    async def get_vehicle_trips(self, vehicle_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None):
        """Get vehicle trips with optional date range filter."""
        from backend.models import TripLog

        trips = await TripLog.find(TripLog.vehicle_uid == vehicle_id).sort("-out_time").to_list()
        return [t for t in trips if t.out_time and self._in_window(t.out_time, start_date, end_date)]

    async def get_driver_trips(self, driver_name: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
        """Get trips by driver name and optional date range."""
        from backend.models import TripLog

        trips = await TripLog.find(TripLog.driver_name == driver_name).sort("-out_time").to_list()
        return [t for t in trips if t.out_time and self._in_window(t.out_time, start_date, end_date)]

    # ====================================================================
    # ANALYTICS
    # ====================================================================

    async def calculate_total_distance(
        self,
        vehicle_id: Optional[int] = None,
        driver_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Calculate total distance traveled for selected filters."""
        from backend.models import TripLog

        filters = []
        if vehicle_id is not None:
            filters.append(TripLog.vehicle_uid == vehicle_id)
        if driver_name is not None:
            filters.append(TripLog.driver_name == driver_name)

        trips = await (TripLog.find(*filters).to_list() if filters else TripLog.find_all().to_list())
        filtered = [
            t
            for t in trips
            if t.status == "Completed" and t.out_time and self._in_window(t.out_time, start_date, end_date)
        ]

        total = sum(max(0.0, t.end_mileage - t.start_mileage) for t in filtered)
        return {
            "trip_count": len(filtered),
            "total_distance": round(total, 3),
            "vehicle_id": vehicle_id,
            "driver_name": driver_name,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }

    async def calculate_fuel_efficiency(
        self,
        vehicle_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Calculate km/l using trip distance and fuel logs."""
        from backend.models import FuelLog

        distance_data = await self.calculate_total_distance(vehicle_id=vehicle_id, start_date=start_date, end_date=end_date)

        fuel_logs = await FuelLog.find(FuelLog.vehicle_uid == vehicle_id).to_list()
        total_liters = 0.0
        for log in fuel_logs:
            try:
                log_date = date.fromisoformat(log.date)
            except ValueError:
                continue
            if start_date and log_date < start_date:
                continue
            if end_date and log_date > end_date:
                continue
            total_liters += log.liters

        total_distance = distance_data["total_distance"]
        efficiency = round(total_distance / total_liters, 3) if total_liters > 0 else 0.0

        return {
            "vehicle_id": vehicle_id,
            "total_distance": total_distance,
            "total_liters": round(total_liters, 3),
            "km_per_liter": efficiency,
        }

    async def get_most_used_routes(self, limit: int = 10):
        """Get most frequent trip purposes (route proxy)."""
        from backend.models import TripLog

        trips = await TripLog.find_all().to_list()
        stats: dict[str, dict[str, Any]] = {}
        for trip in trips:
            key = trip.purpose or "Unspecified"
            row = stats.setdefault(key, {"purpose": key, "trip_count": 0, "total_distance": 0.0})
            row["trip_count"] += 1
            row["total_distance"] += max(0.0, trip.end_mileage - trip.start_mileage)

        ranked = sorted(stats.values(), key=lambda item: item["trip_count"], reverse=True)
        return [{**row, "total_distance": round(row["total_distance"], 3)} for row in ranked[: max(1, limit)]]

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def create_trip_log(self, payload: Any):
        """Backward-compatible helper using start_trip payload format."""
        data = self._to_dict(payload)
        return await self.start_trip(
            vehicle_id=data["vehicle_uid"],
            driver_name=data["driver_name"],
            purpose=data.get("purpose", "General"),
            start_condition=data.get("start_condition", "Good"),
            out_time=data.get("out_time"),
        )

    async def get_trip_log_by_id(self, trip_log_id: int):
        """Backward-compatible alias for get_trip_by_id."""
        return await self.get_trip_by_id(trip_log_id)

    async def get_trip_logs_for_vehicle(self, vehicle_id: int):
        """Backward-compatible alias for get_vehicle_trips."""
        return await self.get_vehicle_trips(vehicle_id)

    async def update_trip_log(self, trip_log_id: int, payload: Any):
        """Backward-compatible update helper."""
        trip = await self.get_trip_by_id(trip_log_id)
        data = self._to_dict(payload)
        for field, value in data.items():
            setattr(trip, field, value)
        trip.updated_at = datetime.now()
        await trip.save()
        return trip

    async def delete_trip_log(self, trip_log_id: int) -> bool:
        """Backward-compatible hard delete helper."""
        trip = await self.get_trip_by_id(trip_log_id)
        await trip.delete()
        logger.info("Trip log deleted: %s", trip_log_id)
        return True
