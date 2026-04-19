"""Shift-Based Contract — role slots filled by any available employee daily."""

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract, ContractType


class RoleBasedContract(BaseContract):
    """
    Shift-Based Contract (was: Role-Based Contract).
    Roles are defined (e.g. 10 Drivers) — any employee with matching
    designation fills the slot each day via Daily Muster.
    """

    role_requirements: List[Dict[str, Any]] = []
    # e.g. [{"designation": "Driver", "count": 5, "daily_rate": 50.0}]

    def __init__(self, **data: Any) -> None:
        data.setdefault("enabled_modules", ["roles", "daily_muster", "attendance"])
        data.setdefault("salary_strategy", "role_based")
        data.setdefault("contract_type", ContractType.SHIFT_BASED)
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        from backend.models.role_contracts import DailyRoleFulfillment
        _, last_day = monthrange(year, month)
        start = datetime(year, month, 1)
        end = datetime(year, month, last_day, 23, 59, 59)
        fulfillments = await DailyRoleFulfillment.find(
            DailyRoleFulfillment.contract_id == self.uid,
            DailyRoleFulfillment.date >= start,
            DailyRoleFulfillment.date <= end,
        ).to_list()
        return sum(f.total_daily_cost for f in fulfillments)

    async def calculate_employee_salary(self, employee_id: int, month: int, year: int) -> float:
        # TODO: Role-based salary via Daily Muster records
        return 0.0

    async def get_required_resources(self) -> Dict[str, Any]:
        return {"roles": self.role_requirements}

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        return {"fulfilled": True, "message": "Shift fulfillment validation not yet implemented"}
