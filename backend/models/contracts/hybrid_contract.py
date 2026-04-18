"""Hybrid contract – combines employees AND inventory (Phase 5A)."""

from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract


class HybridContract(BaseContract):
    """
    Contract with BOTH employees AND inventory/material supply.

    Example: Warehouse management (fixed manager + role-based loaders)
    combined with a material supply component.
    """

    # Fixed employees assigned by ID
    assigned_employee_ids: List[int] = []

    # Role-based employee requirements
    role_requirements: List[Dict[str, Any]] = []
    # Example: [{"role": "Loader", "count": 5, "daily_rate": 40.0}]

    # Inventory / material items
    material_items: List[Dict[str, Any]] = []
    # Example: [{"material_id": 42, "quantity": 500, "unit": "kg"}]

    def __init__(self, **data: Any) -> None:
        data.setdefault("enabled_modules", ["employee", "roles", "inventory", "site"])
        data.setdefault("salary_strategy", "mixed")
        data.setdefault("contract_type", "Labour")
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        """
        Total cost = fixed employee costs + role-based fulfillment costs
        + material movement costs.

        Full implementation in Phase 5B.
        """
        # TODO: Implement hybrid cost calculation in Phase 5B
        return 0.0

    async def calculate_employee_salary(
        self, employee_id: int, month: int, year: int
    ) -> float:
        """
        Determine whether the employee is fixed or role-based and
        calculate accordingly.

        Full implementation in Phase 5B.
        """
        # TODO: Implement hybrid salary calculation in Phase 5B
        return 0.0

    async def get_required_resources(self) -> Dict[str, Any]:
        """Returns both employee and material requirements."""
        return {
            "fixed_employees": len(self.assigned_employee_ids),
            "roles": self.role_requirements,
            "materials": self.material_items,
        }

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        """Validate both employee attendance and material deliveries."""
        # TODO: Implement hybrid validation in Phase 5B
        return {
            "fulfilled": True,
            "message": "Hybrid fulfillment validation not yet implemented",
        }
