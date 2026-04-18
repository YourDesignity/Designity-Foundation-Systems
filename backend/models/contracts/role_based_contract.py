"""Role-based contract – role slots filled by any available employee (Phase 5A)."""

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract


class RoleBasedContract(BaseContract):
    """
    Contract with ROLES defined rather than specific employees.

    Example: "Need 5 Security Guards daily" – any guard can fill the
    slots.  Daily cost is tracked through ``DailyRoleFulfillment``
    documents.
    """

    # Specific fields for role-based contracts
    role_requirements: List[Dict[str, Any]] = []
    # Example:
    # [{"role": "Security Guard", "count": 5, "daily_rate": 50.0}]

    def __init__(self, **data: Any) -> None:
        data.setdefault("enabled_modules", ["roles", "daily_fulfillment", "attendance"])
        data.setdefault("salary_strategy", "role_based")
        data.setdefault("contract_type", "Labour")
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        """Total cost = sum of daily fulfillment costs for the month."""
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

    async def calculate_employee_salary(
        self, employee_id: int, month: int, year: int
    ) -> float:
        """
        Role-based salary = sum of (daily_rate × days worked in each role).

        An employee may work different roles on different days.
        Full implementation in Phase 5B.
        """
        # TODO: Implement role-based salary calculation in Phase 5B
        return 0.0

    async def get_required_resources(self) -> Dict[str, Any]:
        """Returns the role requirements for this contract."""
        return {"roles": self.role_requirements}

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        """Check if all role slots are filled for the given date."""
        # TODO: Check DailyRoleFulfillment records in Phase 5B
        return {
            "fulfilled": True,
            "message": "Role fulfillment validation not yet implemented",
        }
