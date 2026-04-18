"""Fixed-salary calculator – basic_salary + allowance with no complex rules (Phase 5B)."""

from typing import Any, Dict, Optional

from backend.models.salary_config import SalaryConfig
from backend.services.salary.base_calculator import SalaryCalculator


class FixedSalaryCalculator(SalaryCalculator):
    """
    Simplest strategy: employee salary = basic_salary + allowance.

    Used by ``LabourContract`` (salary_strategy = "fixed").
    Any ``SalaryConfig`` passed is ignored; the raw employee fields are used.
    """

    async def calculate_monthly_salary(
        self,
        employee_id: int,
        contract_id: int,
        month: int,
        year: int,
        config: Optional[SalaryConfig] = None,
    ) -> Dict[str, Any]:
        from backend.models.hr import Employee

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            return {
                "employee_id": employee_id,
                "total": 0.0,
                "error": "Employee not found",
            }

        base = emp.basic_salary or 0.0
        allowance = emp.allowance or 0.0
        total = base + allowance

        return {
            "employee_id": employee_id,
            "employee_name": emp.name,
            "month": month,
            "year": year,
            "base_salary": base,
            "allowances": {"default": allowance} if allowance else {},
            "bonuses": {},
            "deductions": {},
            "overtime": 0.0,
            "period_modifiers": {},
            "total": total,
            "breakdown": {"strategy": "fixed"},
        }
