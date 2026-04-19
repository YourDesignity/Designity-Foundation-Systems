"""Dedicated Staff Contract — fixed named employees assigned for contract duration."""

from datetime import datetime
from typing import Any, Dict, List

from backend.models.contracts.base_contract import BaseContract, ContractType


class LabourContract(BaseContract):
    """
    Dedicated Staff Contract (was: Labour Contract).
    Specific named employees are assigned for the full contract duration.
    Example: Construction project with a fixed crew of 20 workers.
    """

    assigned_employee_ids: List[int] = []

    def __init__(self, **data: Any) -> None:
        data.setdefault("enabled_modules", ["employee", "attendance", "site"])
        data.setdefault("salary_strategy", "fixed")
        data.setdefault("contract_type", ContractType.DEDICATED_STAFF)
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        from backend.models.hr import Employee
        total = 0.0
        for emp_id in self.assigned_employee_ids:
            emp = await Employee.find_one(Employee.uid == emp_id)
            if emp:
                total += (emp.basic_salary or 0.0) + (emp.allowance or 0.0)
        return total

    async def calculate_employee_salary(self, employee_id: int, month: int, year: int) -> float:
        from backend.models.hr import Employee
        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            return 0.0
        return (emp.basic_salary or 0.0) + (emp.allowance or 0.0)

    async def get_required_resources(self) -> Dict[str, Any]:
        from backend.models.hr import Employee
        employees = await Employee.find({"uid": {"$in": self.assigned_employee_ids}}).to_list()
        return {
            "employees": [
                {"id": emp.uid, "name": emp.name, "designation": emp.designation, "status": "assigned"}
                for emp in employees
            ]
        }

    async def validate_fulfillment(self, date: datetime) -> Dict[str, Any]:
        return {"fulfilled": True, "message": "Attendance validation not yet implemented"}
