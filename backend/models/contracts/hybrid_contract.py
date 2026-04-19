"""Hybrid Contract — combines multiple contract types under one project."""

from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract, ContractType


class HybridContract(BaseContract):
    """
    Hybrid Contract — combination of workforce and/or goods and/or transport.
    Admin selects which modules to enable when creating.
    """

    assigned_employee_ids: List[int] = []
    role_requirements: List[Dict[str, Any]] = []
    material_items: List[Dict[str, Any]] = []

    def __init__(self, **data: Any) -> None:
        data.setdefault("enabled_modules", ["employee", "roles", "inventory", "site"])
        data.setdefault("salary_strategy", "mixed")
        data.setdefault("contract_type", ContractType.HYBRID)
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        # TODO: Hybrid cost calculation
        return 0.0

    async def calculate_employee_salary(self, employee_id: int, month: int, year: int) -> float:
        # TODO: Hybrid salary calculation
        return 0.0

    async def get_required_resources(self) -> Dict[str, Any]:
        return {
            "fixed_employees": len(self.assigned_employee_ids),
            "roles": self.role_requirements,
            "materials": self.material_items,
        }

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        return {"fulfilled": True, "message": "Hybrid fulfillment validation not yet implemented"}
