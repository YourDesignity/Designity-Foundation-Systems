"""
Fixed-salary calculator.
Includes overtime and deductions from the Overtime/Deduction collections
so payslips accurately reflect what was logged by managers/admins.
"""

from typing import Any, Dict, Optional
from backend.models.salary_config import SalaryConfig
from backend.services.salary.base_calculator import SalaryCalculator


class FixedSalaryCalculator(SalaryCalculator):
    """
    Base salary = basic_salary + allowance.
    Also fetches logged Overtime and Deduction records for the month
    and factors them into the final total.
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
        from backend.models.payroll import Overtime, Deduction
        from backend.models.settings import CompanySettings

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            return {"employee_id": employee_id, "total": 0.0, "error": "Employee not found"}

        base       = emp.basic_salary or 0.0
        allowance  = emp.allowance or 0.0
        work_days  = emp.standard_work_days or 28
        daily_rate = base / work_days if work_days > 0 else 0.0
        hourly_rate = daily_rate / 8  # standard 8-hour day

        # ── Overtime ──────────────────────────────────────────────────
        month_prefix = f"{year}-{month:02d}"
        ot_records = await Overtime.find(
            Overtime.employee_uid == employee_id
        ).to_list()
        ot_records = [r for r in ot_records if r.date.startswith(month_prefix)]

        # Load multipliers from company settings
        settings = await CompanySettings.find_one()
        normal_mult  = (settings.normal_overtime_multiplier  if settings else None) or 1.25
        offday_mult  = (settings.offday_overtime_multiplier  if settings else None) or 1.5

        overtime_total = 0.0
        ot_breakdown   = []
        for r in ot_records:
            mult   = offday_mult if r.type == "Offday" else normal_mult
            amount = r.hours * hourly_rate * mult
            overtime_total += amount
            ot_breakdown.append({
                "date": r.date, "hours": r.hours,
                "type": r.type, "multiplier": mult, "amount": round(amount, 3)
            })

        # ── Deductions ────────────────────────────────────────────────
        ded_records = await Deduction.find(
            Deduction.employee_uid == employee_id,
            Deduction.pay_period == month_prefix,
        ).to_list()

        deductions_total = sum(r.amount for r in ded_records)
        ded_breakdown    = [
            {"reason": r.reason or "Deduction", "amount": r.amount}
            for r in ded_records
        ]

        total = base + allowance + overtime_total - deductions_total

        return {
            "employee_id": employee_id,
            "employee_name": emp.name,
            "month": month,
            "year": year,
            "base_salary": base,
            "allowances": {"default": allowance} if allowance else {},
            "bonuses": {},
            "deductions": {d["reason"]: d["amount"] for d in ded_breakdown},
            "overtime": round(overtime_total, 3),
            "overtime_breakdown": ot_breakdown,
            "period_modifiers": {},
            "total": round(total, 3),
            "breakdown": {
                "strategy": "fixed",
                "daily_rate": round(daily_rate, 3),
                "hourly_rate": round(hourly_rate, 3),
                "overtime_records": len(ot_records),
                "deduction_records": len(ded_records),
            },
        }
