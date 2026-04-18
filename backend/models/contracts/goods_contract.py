"""Goods contract – pure inventory/material supply with no employees (Phase 5A)."""

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract


class GoodsContract(BaseContract):
    """
    Contract for pure inventory / material supply.

    Example: "Supply 1 000 tons of cement over 6 months".
    There are no employee assignments – only material movements.
    """

    # Specific fields for goods contracts
    material_items: List[Dict[str, Any]] = []
    # Example:
    # [{"material_id": 123, "quantity": 1000, "unit": "tons", "unit_price": 150.0}]

    delivery_schedule: List[Dict[str, Any]] = []
    # Example:
    # [{"date": "2026-05-01", "quantity": 200, "status": "pending"}]

    def __init__(self, **data: Any) -> None:
        data.setdefault("enabled_modules", ["inventory", "materials", "delivery"])
        data.setdefault("salary_strategy", "none")  # No employees
        data.setdefault("contract_type", "Goods Supply")
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        """Total cost = sum of outgoing material movements for the month."""
        from backend.models.materials import MaterialMovement

        _, last_day = monthrange(year, month)
        start = datetime(year, month, 1)
        end = datetime(year, month, last_day, 23, 59, 59)

        movements = await MaterialMovement.find(
            MaterialMovement.contract_id == self.uid,
            MaterialMovement.movement_type == "OUT",
            MaterialMovement.created_at >= start,
            MaterialMovement.created_at <= end,
        ).to_list()

        return sum(m.total_cost or 0 for m in movements)

    async def calculate_employee_salary(
        self, employee_id: int, month: int, year: int
    ) -> float:
        """Goods contracts have no employees – always returns 0."""
        return 0.0

    async def get_required_resources(self) -> Dict[str, Any]:
        """Returns the list of materials required by this contract."""
        return {"materials": self.material_items}

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        """Check whether deliveries are on schedule for the given date."""
        # TODO: Check material movement records in Phase 5B
        return {
            "fulfilled": True,
            "message": "Delivery schedule validation not yet implemented",
        }
