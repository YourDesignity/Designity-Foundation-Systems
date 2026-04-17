"""Service layer for maintenance operations."""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class MaintenanceService(BaseService):
    """Maintenance, fuel, and reminders service."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _parse_iso_day(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    # ====================================================================
    # MAINTENANCE EVENTS
    # ====================================================================

    async def record_maintenance(
        self,
        vehicle_id: int,
        service_type: str,
        cost: float,
        service_date: date,
        next_due_date: Optional[date] = None,
        notes: Optional[str] = None,
    ):
        """Log a completed maintenance event."""
        from backend.models import MaintenanceLog, Vehicle

        if cost < 0:
            self.raise_bad_request("Maintenance cost cannot be negative")

        vehicle = await Vehicle.find_one(Vehicle.uid == vehicle_id)
        if not vehicle:
            self.raise_not_found("Vehicle not found")

        uid = await self.get_next_uid("vehicle_maintenance")
        row = MaintenanceLog(
            uid=uid,
            vehicle_uid=vehicle.uid,
            vehicle_plate=vehicle.plate,
            service_type=service_type,
            cost=cost,
            service_date=service_date.isoformat(),
            next_due_date=next_due_date.isoformat() if next_due_date else None,
            notes=notes,
        )
        await row.insert()
        logger.info("Maintenance recorded: vehicle %s service=%s", vehicle.plate, service_type)
        return row

    async def update_maintenance(self, maintenance_id: int, payload: Any):
        """Update existing maintenance record."""
        record = await self.get_maintenance_by_id(maintenance_id)
        data = self._to_dict(payload)

        if "cost" in data and float(data["cost"]) < 0:
            self.raise_bad_request("Maintenance cost cannot be negative")

        for key, value in data.items():
            setattr(record, key, value)
        record.updated_at = datetime.now()
        await record.save()
        return record

    async def get_maintenance_by_id(self, maintenance_id: int):
        """Get maintenance record by UID."""
        from backend.models import MaintenanceLog

        row = await MaintenanceLog.find_one(MaintenanceLog.uid == maintenance_id)
        if not row:
            self.raise_not_found("Maintenance record not found")
        return row

    async def schedule_maintenance(
        self,
        vehicle_id: int,
        service_type: str,
        due_date: date,
        estimated_cost: float = 0.0,
        notes: Optional[str] = None,
    ):
        """Create a scheduled maintenance entry."""
        return await self.record_maintenance(
            vehicle_id=vehicle_id,
            service_type=service_type,
            cost=max(0.0, estimated_cost),
            service_date=due_date,
            next_due_date=due_date,
            notes=f"[SCHEDULED] {notes or ''}".strip(),
        )

    async def get_upcoming_maintenance(self, within_days: int = 30):
        """Get maintenance entries with due dates inside forward window."""
        from backend.models import MaintenanceLog

        if within_days < 0:
            self.raise_bad_request("within_days must be non-negative")

        today = date.today()
        window_end = today + timedelta(days=within_days)
        rows = await MaintenanceLog.find_all().to_list()

        result = []
        for row in rows:
            due = self._parse_iso_day(row.next_due_date)
            if due and today <= due <= window_end:
                result.append(row)
        return sorted(result, key=lambda item: item.next_due_date or "")

    async def get_overdue_maintenance(self):
        """Get maintenance entries whose next_due_date is past."""
        from backend.models import MaintenanceLog

        today = date.today()
        rows = await MaintenanceLog.find_all().to_list()
        overdue = []
        for row in rows:
            due_date = self._parse_iso_day(row.next_due_date)
            if due_date and due_date < today:
                overdue.append(row)
        return sorted(overdue, key=lambda item: item.next_due_date or "")

    # ====================================================================
    # FUEL OPERATIONS
    # ====================================================================

    async def record_fuel_log(
        self,
        vehicle_id: int,
        log_date: date,
        liters: float,
        cost: float,
        odometer: float,
        filled_by: Optional[str] = None,
    ):
        """Log a fuel fill-up and update vehicle odometer."""
        from backend.models import FuelLog, Vehicle

        if liters <= 0:
            self.raise_bad_request("liters must be greater than 0")
        if cost < 0:
            self.raise_bad_request("cost cannot be negative")

        vehicle = await Vehicle.find_one(Vehicle.uid == vehicle_id)
        if not vehicle:
            self.raise_not_found("Vehicle not found")

        uid = await self.get_next_uid("vehicle_fuel")
        log = FuelLog(
            uid=uid,
            vehicle_uid=vehicle.uid,
            vehicle_plate=vehicle.plate,
            date=log_date.isoformat(),
            liters=liters,
            cost=cost,
            odometer=odometer,
            filled_by=filled_by,
        )
        await log.insert()

        if odometer > vehicle.current_mileage:
            vehicle.current_mileage = odometer
            vehicle.updated_at = datetime.now()
            await vehicle.save()

        return log

    async def calculate_fuel_cost(self, month: int, year: int, vehicle_id: Optional[int] = None) -> dict:
        """Calculate monthly fuel cost totals."""
        from backend.models import FuelLog

        filters = [FuelLog.vehicle_uid == vehicle_id] if vehicle_id is not None else []
        logs = await (FuelLog.find(*filters).to_list() if filters else FuelLog.find_all().to_list())

        selected = []
        for log in logs:
            parsed = self._parse_iso_day(log.date)
            if parsed and parsed.month == month and parsed.year == year:
                selected.append(log)

        total_cost = sum(log.cost for log in selected)
        total_liters = sum(log.liters for log in selected)
        return {
            "vehicle_id": vehicle_id,
            "month": month,
            "year": year,
            "records": len(selected),
            "total_liters": round(total_liters, 3),
            "total_cost": round(total_cost, 3),
        }

    async def calculate_fuel_efficiency_trend(self, vehicle_id: int, months: int = 6):
        """Return trailing monthly fuel efficiency trend (km/l)."""
        from dateutil.relativedelta import relativedelta
        from backend.models import FuelLog, TripLog

        if months <= 0:
            self.raise_bad_request("months must be greater than 0")

        logs = await FuelLog.find(FuelLog.vehicle_uid == vehicle_id).to_list()
        trips = await TripLog.find(TripLog.vehicle_uid == vehicle_id, TripLog.status == "Completed").to_list()

        month_anchor = date.today().replace(day=1)
        series = []
        for idx in range(months):
            period = month_anchor - relativedelta(months=idx)
            month, year = period.month, period.year

            month_liters = 0.0
            for row in logs:
                parsed = self._parse_iso_day(row.date)
                if parsed and parsed.month == month and parsed.year == year:
                    month_liters += row.liters
            month_distance = sum(
                max(0.0, trip.end_mileage - trip.start_mileage)
                for trip in trips
                if trip.out_time and trip.out_time.month == month and trip.out_time.year == year
            )
            km_per_liter = round(month_distance / month_liters, 3) if month_liters > 0 else 0.0
            series.append(
                {
                    "month": month,
                    "year": year,
                    "distance": round(month_distance, 3),
                    "liters": round(month_liters, 3),
                    "km_per_liter": km_per_liter,
                }
            )

        return sorted(series, key=lambda item: (item["year"], item["month"]))

    # ====================================================================
    # ALERTS
    # ====================================================================

    async def send_maintenance_reminders(self, within_days: int = 7):
        """Produce reminder payload for upcoming maintenance."""
        upcoming = await self.get_upcoming_maintenance(within_days=within_days)
        reminders = []
        for row in upcoming:
            due = self._parse_iso_day(row.next_due_date)
            reminders.append(
                {
                    "maintenance_id": row.uid,
                    "vehicle_uid": row.vehicle_uid,
                    "vehicle_plate": row.vehicle_plate,
                    "service_type": row.service_type,
                    "due_date": row.next_due_date,
                    "days_remaining": (due - date.today()).days if due else None,
                }
            )
        return reminders

    async def check_maintenance_due(self, vehicle_id: int, as_of: Optional[date] = None) -> dict:
        """Check if a vehicle has overdue maintenance."""
        from backend.models import MaintenanceLog

        current_day = as_of or date.today()
        rows = await MaintenanceLog.find(MaintenanceLog.vehicle_uid == vehicle_id).sort("-service_date").to_list()
        if not rows:
            return {"vehicle_id": vehicle_id, "is_due": False, "reason": "No maintenance history"}

        latest = rows[0]
        due = self._parse_iso_day(latest.next_due_date)
        if due and due <= current_day:
            return {"vehicle_id": vehicle_id, "is_due": True, "due_date": due.isoformat(), "service_type": latest.service_type}
        return {"vehicle_id": vehicle_id, "is_due": False, "due_date": due.isoformat() if due else None}

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def create_maintenance_log(self, payload: Any):
        """Backward-compatible create helper."""
        data = self._to_dict(payload)
        service_date = self._parse_iso_day(data.get("service_date"))
        if not service_date:
            self.raise_bad_request("service_date is required in YYYY-MM-DD format")
        next_due = self._parse_iso_day(data.get("next_due_date"))
        return await self.record_maintenance(
            vehicle_id=data["vehicle_uid"],
            service_type=data["service_type"],
            cost=float(data.get("cost", 0.0)),
            service_date=service_date,
            next_due_date=next_due,
            notes=data.get("notes"),
        )

    async def get_maintenance_log_by_id(self, log_id: int):
        """Backward-compatible alias for get_maintenance_by_id."""
        return await self.get_maintenance_by_id(log_id)

    async def get_maintenance_logs_for_vehicle(self, vehicle_id: int):
        """Backward-compatible vehicle history alias."""
        from backend.models import MaintenanceLog

        return await MaintenanceLog.find(MaintenanceLog.vehicle_uid == vehicle_id).sort("-service_date").to_list()

    async def update_maintenance_log(self, log_id: int, payload: Any):
        """Backward-compatible update alias."""
        return await self.update_maintenance(log_id, payload)

    async def delete_maintenance_log(self, log_id: int) -> bool:
        """Backward-compatible hard delete helper."""
        row = await self.get_maintenance_by_id(log_id)
        await row.delete()
        logger.info("Maintenance log deleted: %s", log_id)
        return True
