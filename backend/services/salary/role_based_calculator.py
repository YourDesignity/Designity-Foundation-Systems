"""Role-based salary calculator – pay based on daily rates per role (Phase 5B)."""

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, Optional

from backend.models.salary_config import SalaryConfig
from backend.services.salary.base_calculator import SalaryCalculator


class RoleBasedCalculator(SalaryCalculator):
    """
    Role-based strategy: salary = sum of (daily_rate × days worked per role).

    An employee may work different roles on different days; each role carries
    its own ``daily_rate`` drawn from the ``DailyRoleFulfillment`` records.

    Used by ``RoleBasedContract`` (salary_strategy = "role_based").
    """

    async def calculate_monthly_salary(
        self,
        employee_id: int,
        contract_id: int,
        month: int,
        year: int,
        config: Optional[SalaryConfig] = None,
    ) -> Dict[str, Any]:
        from backend.models.role_contracts import DailyRoleFulfillment

        _, last_day = monthrange(year, month)
        start = datetime(year, month, 1)
        end = datetime(year, month, last_day, 23, 59, 59)

        fulfillments = await DailyRoleFulfillment.find(
            DailyRoleFulfillment.contract_id == contract_id,
            DailyRoleFulfillment.date >= start,
            DailyRoleFulfillment.date <= end,
        ).to_list()

        # Aggregate earnings per role
        role_earnings: Dict[str, float] = {}
        for record in fulfillments:
            for slot in getattr(record, "filled_slots", []):
                if getattr(slot, "employee_id", None) != employee_id:
                    continue
                role = getattr(slot, "designation", "Unknown")
                daily_rate = getattr(slot, "daily_rate", 0.0) or 0.0
                role_earnings[role] = role_earnings.get(role, 0.0) + daily_rate

        total = sum(role_earnings.values())

        # Try to get employee name
        emp_name = f"Employee #{employee_id}"
        try:
            from backend.models.hr import Employee

            emp = await Employee.find_one(Employee.uid == employee_id)
            if emp:
                emp_name = emp.name
        except Exception:
            pass

        return {
            "employee_id": employee_id,
            "employee_name": emp_name,
            "month": month,
            "year": year,
            "base_salary": total,
            "allowances": {},
            "bonuses": {},
            "deductions": {},
            "overtime": 0.0,
            "period_modifiers": {},
            "total": total,
            "breakdown": {
                "strategy": "role_based",
                "role_earnings": role_earnings,
            },
        }
