"""Labour contract – fixed employees assigned to a contract (Phase 5A)."""

from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract


class LabourContract(BaseContract):
    """
    Contract with FIXED employees assigned.

    Example: Construction project with a specific crew.
    Each employee is individually named and their salary is based on
    their personal ``basic_salary + allowance`` fields.
    """

    # Specific fields for labour contracts
    assigned_employee_ids: List[int] = []

    def __init__(self, **data: Any) -> None:
        # Set sensible defaults for a labour contract before validation
        data.setdefault("enabled_modules", ["employee", "attendance", "site"])
        data.setdefault("salary_strategy", "fixed")
        data.setdefault("contract_type", "Labour")
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        """Total cost = sum of all assigned employees' base salaries."""
        from backend.models.hr import Employee

        total = 0.0
        for emp_id in self.assigned_employee_ids:
            emp = await Employee.find_one(Employee.uid == emp_id)
            if emp:
                total += (emp.basic_salary or 0.0) + (emp.allowance or 0.0)
        return total

    async def calculate_employee_salary(
        self, employee_id: int, month: int, year: int
    ) -> float:
        """
        Fixed employee salary = basic_salary + allowance.

        Attendance-based adjustments can be layered on top in Phase 5B.
        """
        from backend.models.hr import Employee

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            return 0.0
        return (emp.basic_salary or 0.0) + (emp.allowance or 0.0)

    async def get_required_resources(self) -> Dict[str, Any]:
        """Returns the list of assigned employees with basic metadata."""
        from backend.models.hr import Employee

        employees = await Employee.find(
            {"uid": {"$in": self.assigned_employee_ids}}
        ).to_list()

        return {
            "employees": [
                {
                    "id": emp.uid,
                    "name": emp.name,
                    "designation": emp.designation,
                    "status": "assigned",
                }
                for emp in employees
            ]
        }

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        """Check if all assigned employees are present on the given date."""
        # TODO: Implement attendance-record check in Phase 5B
        return {
            "fulfilled": True,
            "message": "Attendance validation not yet implemented",
        }
