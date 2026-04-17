"""Service layer for vehicle operations."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class VehicleService(BaseService):
    """Vehicle lifecycle, assignment, and operating-cost logic."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    # ====================================================================
    # CRUD OPERATIONS
    # ====================================================================

    async def register_vehicle(self, payload: Any):
        """Register a vehicle with unique uppercase plate."""
        from backend.models import Vehicle

        data = self._to_dict(payload)
        plate = (data.get("plate") or "").strip().upper()
        if not plate:
            self.raise_bad_request("plate is required")

        existing = await Vehicle.find_one(Vehicle.plate == plate)
        if existing:
            self.raise_bad_request(f"Plate {plate} already exists")

        uid = await self.get_next_uid("vehicles")
        vehicle = Vehicle(
            uid=uid,
            model=data.get("model", ""),
            plate=plate,
            type=data.get("type", "General"),
            status=data.get("status", "Available"),
            current_mileage=float(data.get("current_mileage", 0.0)),
            registration_expiry=data.get("registration_expiry"),
            insurance_expiry=data.get("insurance_expiry"),
            pollution_expiry=data.get("pollution_expiry"),
            specs={
                "assigned_driver": None,
                "assigned_driver_id": None,
            },
        )
        await vehicle.insert()
        logger.info("Vehicle registered: %s (ID: %s)", vehicle.plate, uid)
        return vehicle

    async def update_vehicle(self, vehicle_id: int, payload: Any):
        """Update vehicle details."""
        vehicle = await self.get_vehicle_by_id(vehicle_id)
        data = self._to_dict(payload)

        if "plate" in data:
            new_plate = str(data["plate"]).strip().upper()
            if not new_plate:
                self.raise_bad_request("plate cannot be empty")
            duplicate = await self.get_vehicle_by_plate(new_plate, raise_if_missing=False)
            if duplicate and duplicate.uid != vehicle.uid:
                self.raise_bad_request(f"Plate {new_plate} already exists")
            data["plate"] = new_plate

        for key, value in data.items():
            setattr(vehicle, key, value)
        vehicle.updated_at = datetime.now()
        await vehicle.save()

        logger.info("Vehicle updated: ID %s", vehicle_id)
        return vehicle

    async def deactivate_vehicle(self, vehicle_id: int, deactivated_by: Optional[int] = None):
        """Soft-delete/deactivate vehicle."""
        vehicle = await self.get_vehicle_by_id(vehicle_id)
        vehicle.is_active = False
        vehicle.status = "Inactive"
        vehicle.updated_at = datetime.now()
        await vehicle.save()
        logger.warning("Vehicle deactivated: %s by user %s", vehicle.plate, deactivated_by)
        return vehicle

    async def get_vehicle_by_id(self, vehicle_id: int):
        """Get vehicle by UID."""
        from backend.models import Vehicle

        vehicle = await Vehicle.find_one(Vehicle.uid == vehicle_id)
        if not vehicle:
            self.raise_not_found("Vehicle not found")
        return vehicle

    async def get_vehicle_by_plate(self, plate: str, raise_if_missing: bool = True):
        """Get vehicle by normalized plate number."""
        from backend.models import Vehicle

        vehicle = await Vehicle.find_one(Vehicle.plate == plate.strip().upper())
        if not vehicle and raise_if_missing:
            self.raise_not_found("Vehicle not found")
        return vehicle

    async def get_all_vehicles(self, status: Optional[str] = None, vehicle_type: Optional[str] = None):
        """Get vehicles with optional status/type filters."""
        from backend.models import Vehicle

        filters = []
        if status:
            filters.append(Vehicle.status == status)
        if vehicle_type:
            filters.append(Vehicle.type == vehicle_type)
        return await (Vehicle.find(*filters).sort("+uid").to_list() if filters else Vehicle.find_all().sort("+uid").to_list())

    # ====================================================================
    # ASSIGNMENT OPERATIONS
    # ====================================================================

    async def assign_vehicle_to_driver(
        self,
        vehicle_id: int,
        driver_name: str,
        driver_id: Optional[int] = None,
        assigned_by: Optional[int] = None,
    ):
        """Mark vehicle assigned to a driver."""
        vehicle = await self.get_vehicle_by_id(vehicle_id)
        if vehicle.status not in {"Available", "Inactive"}:
            self.raise_bad_request("Vehicle is not available for assignment")

        specs = dict(vehicle.specs or {})
        if specs.get("assigned_driver"):
            self.raise_bad_request("Vehicle is already assigned to a driver")

        specs["assigned_driver"] = driver_name
        specs["assigned_driver_id"] = driver_id
        specs["assigned_at"] = datetime.now().isoformat()
        specs["assigned_by"] = assigned_by
        vehicle.specs = specs
        vehicle.status = "Assigned"
        vehicle.updated_at = datetime.now()
        await vehicle.save()

        logger.info("Vehicle %s assigned to %s", vehicle.plate, driver_name)
        return vehicle

    async def release_vehicle(self, vehicle_id: int, released_by: Optional[int] = None):
        """Release vehicle from current driver assignment."""
        vehicle = await self.get_vehicle_by_id(vehicle_id)
        specs = dict(vehicle.specs or {})
        specs["assigned_driver"] = None
        specs["assigned_driver_id"] = None
        specs["released_at"] = datetime.now().isoformat()
        specs["released_by"] = released_by
        vehicle.specs = specs
        if vehicle.status != "On Trip":
            vehicle.status = "Available"
        vehicle.updated_at = datetime.now()
        await vehicle.save()

        logger.info("Vehicle %s released", vehicle.plate)
        return vehicle

    async def get_available_vehicles(self):
        """Return active vehicles that are not assigned/on trip."""
        vehicles = await self.get_all_vehicles()
        return [
            v
            for v in vehicles
            if v.is_active and v.status == "Available" and not (v.specs or {}).get("assigned_driver")
        ]

    # ====================================================================
    # MAINTENANCE OPERATIONS
    # ====================================================================

    async def schedule_maintenance(
        self,
        vehicle_id: int,
        service_type: str,
        due_date: date,
        estimated_cost: float = 0.0,
        notes: Optional[str] = None,
    ):
        """Schedule maintenance by creating a scheduled maintenance log entry."""
        from backend.models import MaintenanceLog

        vehicle = await self.get_vehicle_by_id(vehicle_id)
        uid = await self.get_next_uid("vehicle_maintenance")
        log = MaintenanceLog(
            uid=uid,
            vehicle_uid=vehicle.uid,
            vehicle_plate=vehicle.plate,
            service_type=service_type,
            cost=max(0.0, float(estimated_cost)),
            service_date=due_date.isoformat(),
            next_due_date=due_date.isoformat(),
            notes=f"[SCHEDULED] {notes or ''}".strip(),
        )
        await log.insert()
        logger.info("Maintenance scheduled for vehicle %s on %s", vehicle.plate, due_date)
        return log

    async def record_maintenance(
        self,
        vehicle_id: int,
        service_type: str,
        cost: float,
        service_date: date,
        next_due_date: Optional[date] = None,
        notes: Optional[str] = None,
    ):
        """Record completed maintenance event."""
        from backend.models import MaintenanceLog

        if cost < 0:
            self.raise_bad_request("Maintenance cost cannot be negative")

        vehicle = await self.get_vehicle_by_id(vehicle_id)
        uid = await self.get_next_uid("vehicle_maintenance")
        log = MaintenanceLog(
            uid=uid,
            vehicle_uid=vehicle.uid,
            vehicle_plate=vehicle.plate,
            service_type=service_type,
            cost=float(cost),
            service_date=service_date.isoformat(),
            next_due_date=next_due_date.isoformat() if next_due_date else None,
            notes=notes,
        )
        await log.insert()

        logger.info("Maintenance recorded for vehicle %s", vehicle.plate)
        return log

    async def get_maintenance_history(self, vehicle_id: int):
        """Get all maintenance records for vehicle."""
        from backend.models import MaintenanceLog

        await self.get_vehicle_by_id(vehicle_id)
        return await MaintenanceLog.find(MaintenanceLog.vehicle_uid == vehicle_id).sort("-service_date").to_list()

    async def get_vehicles_needing_maintenance(self, as_of: Optional[date] = None):
        """Return vehicles with overdue regulatory/maintenance dates."""
        from backend.models import MaintenanceLog

        today = as_of or date.today()
        vehicles = await self.get_all_vehicles()
        due = []

        for vehicle in vehicles:
            overdue_reasons = []
            for label, raw_value in (
                ("registration", vehicle.registration_expiry),
                ("insurance", vehicle.insurance_expiry),
                ("pollution", vehicle.pollution_expiry),
            ):
                parsed = self._parse_date(raw_value)
                if parsed and parsed < today:
                    overdue_reasons.append(f"{label} expired")

            latest_maintenance = await MaintenanceLog.find(MaintenanceLog.vehicle_uid == vehicle.uid).sort("-service_date").first_or_none()
            if latest_maintenance and latest_maintenance.next_due_date:
                next_due = self._parse_date(latest_maintenance.next_due_date)
                if next_due and next_due < today:
                    overdue_reasons.append("maintenance overdue")

            if overdue_reasons:
                due.append({"vehicle": vehicle, "reasons": overdue_reasons})

        return due

    # ====================================================================
    # COST REPORTS
    # ====================================================================

    async def calculate_vehicle_operating_cost(self, vehicle_id: int, month: int, year: int) -> dict:
        """Calculate monthly operating cost (fuel + maintenance + expenses)."""
        from backend.models import FuelLog, MaintenanceLog, VehicleExpense

        vehicle = await self.get_vehicle_by_id(vehicle_id)
        fuel = await FuelLog.find(FuelLog.vehicle_uid == vehicle.uid).to_list()
        maintenance = await MaintenanceLog.find(MaintenanceLog.vehicle_uid == vehicle.uid).to_list()
        expenses = await VehicleExpense.find(VehicleExpense.vehicle_uid == vehicle.uid).to_list()

        fuel_cost = 0.0
        for row in fuel:
            parsed = self._parse_date(row.date)
            if parsed and parsed.month == month and parsed.year == year:
                fuel_cost += row.cost

        maintenance_cost = 0.0
        for row in maintenance:
            parsed = self._parse_date(row.service_date)
            if parsed and parsed.month == month and parsed.year == year:
                maintenance_cost += row.cost

        expense_cost = 0.0
        for row in expenses:
            parsed = self._parse_date(row.date)
            if parsed and parsed.month == month and parsed.year == year:
                expense_cost += row.amount

        total = round(fuel_cost + maintenance_cost + expense_cost, 3)
        return {
            "vehicle_id": vehicle.uid,
            "plate": vehicle.plate,
            "month": month,
            "year": year,
            "fuel_cost": round(fuel_cost, 3),
            "maintenance_cost": round(maintenance_cost, 3),
            "expense_cost": round(expense_cost, 3),
            "total_operating_cost": total,
        }

    async def get_most_expensive_vehicles(self, top_n: int = 5, month: Optional[int] = None, year: Optional[int] = None):
        """Rank vehicles by operating cost."""
        vehicles = await self.get_all_vehicles()
        report_month = month or date.today().month
        report_year = year or date.today().year

        rows = []
        for vehicle in vehicles:
            costs = await self.calculate_vehicle_operating_cost(vehicle.uid, report_month, report_year)
            rows.append(costs)

        rows.sort(key=lambda item: item["total_operating_cost"], reverse=True)
        return rows[: max(1, top_n)]

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def create_vehicle(self, payload: Any):
        """Backward-compatible alias to register_vehicle."""
        return await self.register_vehicle(payload)

    async def get_vehicles(self):
        """Backward-compatible alias for get_all_vehicles."""
        return await self.get_all_vehicles()

    async def delete_vehicle(self, vehicle_id: int) -> bool:
        """Backward-compatible alias for deactivate_vehicle."""
        await self.deactivate_vehicle(vehicle_id)
        return True
