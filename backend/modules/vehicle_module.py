"""Vehicle / fleet operations module for contracts."""

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, List

from backend.modules.base_module import ContractModule


class VehicleModule(ContractModule):
    """
    Module for tracking vehicle/fleet costs for contracts.
    Handles trip logs, fuel consumption, and vehicle expenses.
    """

    module_name = "vehicle"
    required_models = ["Vehicle", "TripLog", "VehicleExpense"]

    async def initialize(self, contract: Any) -> Dict[str, Any]:
        """Initialize vehicle module for contract."""
        from backend.models.vehicles import TripLog

        # TripLog records linked to a contract are identified by a contract_uid
        # stored in the specs dict (e.g. specs["contract_uid"] == contract.uid).
        # This is the current linking convention until a dedicated FK is added.
        trips = await TripLog.find(
            {"specs.contract_uid": contract.uid}
        ).to_list()

        return {
            "module": self.module_name,
            "status": "initialized",
            "total_trips": len(trips),
        }

    async def calculate_cost(
        self,
        contract: Any,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Calculate total vehicle costs for this contract for the given month.

        Cost = VehicleExpense amounts linked to this contract for the month.
        Trip distance statistics are also computed when available.
        """
        from backend.models.vehicles import TripLog, VehicleExpense

        _, last_day = monthrange(year, month)
        start_dt = datetime(year, month, 1)
        end_dt = datetime(year, month, last_day, 23, 59, 59)

        # Expenses linked via specs["contract_uid"]
        expenses = await VehicleExpense.find(
            {
                "specs.contract_uid": contract.uid,
                "created_at": {"$gte": start_dt, "$lte": end_dt},
            }
        ).to_list()

        expense_cost = float(sum(e.amount for e in expenses))

        # Trip statistics for the same period
        trips = await TripLog.find(
            {
                "specs.contract_uid": contract.uid,
                "created_at": {"$gte": start_dt, "$lte": end_dt},
            }
        ).to_list()

        total_km = float(sum(
            max((t.end_mileage or 0.0) - (t.start_mileage or 0.0), 0.0) for t in trips
        ))
        total_cost = expense_cost

        return {
            "module": self.module_name,
            "total_cost": total_cost,
            "fuel_cost": 0.0,  # Fuel tracked separately via VehicleExpense category
            "other_expenses": expense_cost,
            "total_trips": len(trips),
            "total_kilometers": total_km,
            "cost_per_km": total_cost / total_km if total_km > 0 else 0.0,
        }

    async def validate(
        self,
        contract: Any,
        date: Any,
    ) -> Dict[str, Any]:
        """
        Validate vehicle availability and assignments for a given date.
        """
        from backend.models.vehicles import TripLog

        if isinstance(date, datetime):
            target_date = date.date()
        elif isinstance(date, str):
            from datetime import datetime as _dt
            target_date = _dt.fromisoformat(date).date()
        else:
            target_date = date  # already a datetime.date

        start_dt = datetime(target_date.year, target_date.month, target_date.day)
        end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)

        trips = await TripLog.find(
            {
                "specs.contract_uid": contract.uid,
                "created_at": {"$gte": start_dt, "$lte": end_dt},
            }
        ).to_list()

        return {
            "module": self.module_name,
            "is_valid": True,
            "date": target_date.isoformat(),
            "trips_scheduled": len(trips),
            "issues": [],
            "warnings": [],
        }

    async def get_resource_requirements(self, contract: Any) -> Dict[str, Any]:
        """Get vehicle requirements for this contract."""
        from backend.models.vehicles import TripLog, Vehicle

        trips = await TripLog.find(
            {"specs.contract_uid": contract.uid}
        ).to_list()

        vehicle_uids = list({t.vehicle_uid for t in trips})
        vehicles = await Vehicle.find(
            Vehicle.uid.in_(vehicle_uids)
        ).to_list()

        return {
            "module": self.module_name,
            "total_vehicles": len(vehicles),
            "vehicles": [
                {
                    "id": v.uid,
                    "plate_number": v.plate,
                    "vehicle_type": v.type,
                }
                for v in vehicles
            ],
        }
