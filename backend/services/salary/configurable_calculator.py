"""JSON-driven configurable salary calculator (Phase 5B)."""

from calendar import monthrange
from datetime import date, datetime
from typing import Any, Dict, Optional

from backend.models.salary_config import BonusRule, DeductionRule, OvertimeRule, PeriodModifier, SalaryConfig
from backend.services.salary.base_calculator import SalaryCalculator


class ConfigurableSalaryCalculator(SalaryCalculator):
    """
    JSON-driven salary calculator.

    Applies all configurable rules dynamically:
    - Allowances (transport, food, housing, …)
    - Attendance-based pro-rating
    - Overtime (placeholder – timesheet integration in a future phase)
    - Period modifiers (Ramadan 20 %, Eid flat bonus, …)
    - Bonuses (perfect attendance, performance, …)
    - Deductions (absence, late arrival, …)
    """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def calculate_monthly_salary(
        self,
        employee_id: int,
        contract_id: int,
        month: int,
        year: int,
        config: Optional[SalaryConfig] = None,
    ) -> Dict[str, Any]:
        """Calculate salary with ALL configurable rules applied."""

        if config is None:
            config = SalaryConfig()

        # ── Fetch employee ────────────────────────────────────────────
        from backend.models.hr import Employee

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            return {
                "employee_id": employee_id,
                "total": 0.0,
                "error": "Employee not found",
            }

        # ── Initialise result skeleton ────────────────────────────────
        result: Dict[str, Any] = {
            "employee_id": employee_id,
            "employee_name": emp.name,
            "month": month,
            "year": year,
            "base_salary": emp.basic_salary or 0.0,
            "allowances": {},
            "bonuses": {},
            "deductions": {},
            "overtime": 0.0,
            "period_modifiers": {},
            "total": 0.0,
            "breakdown": {},
        }

        # ── 1. Allowances ─────────────────────────────────────────────
        total_allowances = 0.0
        for name, amount in config.allowances.items():
            result["allowances"][name] = amount
            total_allowances += amount

        if emp.allowance:
            result["allowances"]["default"] = emp.allowance
            total_allowances += emp.allowance

        # ── 2. Attendance-based pro-rating ────────────────────────────
        base_amount = emp.basic_salary or 0.0

        if config.attendance_required:
            attendance_data = await self._get_attendance_data(employee_id, month, year)
            result["breakdown"]["attendance"] = attendance_data

            if config.pro_rate_on_absence:
                factor = attendance_data["rate"]
                base_amount *= factor
                total_allowances *= factor

        # ── 3. Overtime ───────────────────────────────────────────────
        if config.overtime.enabled:
            overtime_data = await self._calculate_overtime(
                employee_id, month, year, config.overtime, emp
            )
            result["overtime"] = overtime_data["total_amount"]
            result["breakdown"]["overtime"] = overtime_data

        # ── 4. Period modifiers (Ramadan, holidays) ───────────────────
        period_modifier_total = 0.0
        for modifier in config.period_modifiers:
            if self._is_in_period(month, year, modifier):
                amount = self._apply_period_modifier(modifier, base_amount, total_allowances)
                period_modifier_total += amount
                result["period_modifiers"][modifier.name] = amount

        # ── 5. Bonuses ────────────────────────────────────────────────
        total_bonuses = 0.0
        for bonus_rule in config.bonuses:
            bonus_amount = await self._calculate_bonus(
                bonus_rule, employee_id, month, year, result["breakdown"]
            )
            if bonus_amount > 0:
                result["bonuses"][bonus_rule.name] = bonus_amount
                total_bonuses += bonus_amount

        # ── 6. Deductions ─────────────────────────────────────────────
        total_deductions = 0.0
        for deduction_rule in config.deductions:
            deduction_amount = await self._calculate_deduction(
                deduction_rule, employee_id, month, year, result["breakdown"]
            )
            if deduction_amount > 0:
                result["deductions"][deduction_rule.name] = deduction_amount
                total_deductions += deduction_amount

        # ── 7. Grand total ────────────────────────────────────────────
        result["total"] = (
            base_amount
            + total_allowances
            + result["overtime"]
            + period_modifier_total
            + total_bonuses
            - total_deductions
        )

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_attendance_data(
        self, employee_id: int, month: int, year: int
    ) -> Dict[str, Any]:
        """Return attendance statistics for the given month."""
        from backend.models.hr import Attendance

        _, last_day = monthrange(year, month)
        # Attendance.date is stored as a string "YYYY-MM-DD"
        prefix = f"{year}-{month:02d}-"

        records = await Attendance.find(
            Attendance.employee_uid == employee_id,
        ).to_list()

        # Filter by month prefix on the date string
        month_records = [r for r in records if (r.date or "").startswith(prefix)]

        total_days = len(month_records)
        present_days = sum(1 for r in month_records if r.status == "Present")
        absent_days = total_days - present_days

        return {
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "rate": present_days / total_days if total_days > 0 else 0.0,
        }

    def _is_in_period(self, month: int, year: int, modifier: PeriodModifier) -> bool:
        """Return True if the given month overlaps with the modifier's date range."""
        _, last_day = monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        return not (modifier.end_date < month_start or modifier.start_date > month_end)

    def _apply_period_modifier(
        self,
        modifier: PeriodModifier,
        base_amount: float,
        total_allowances: float,
    ) -> float:
        """Calculate the bonus/modifier amount for a period (e.g. Ramadan)."""
        if modifier.modifier_type == "percentage":
            applicable = 0.0
            if "base_salary" in modifier.applies_to:
                applicable += base_amount
            if "allowances" in modifier.applies_to:
                applicable += total_allowances
            return applicable * (modifier.value / 100.0)

        if modifier.modifier_type == "fixed_amount":
            return modifier.value

        return 0.0

    async def _calculate_bonus(
        self,
        bonus_rule: BonusRule,
        employee_id: int,
        month: int,
        year: int,
        breakdown: Dict[str, Any],
    ) -> float:
        """Calculate bonus amount based on the rule's condition."""
        if bonus_rule.condition == "perfect_attendance":
            attendance = breakdown.get("attendance", {})
            if attendance.get("absent_days", 0) == 0 and attendance.get("total_days", 0) > 0:
                if bonus_rule.bonus_type == "fixed_amount":
                    return bonus_rule.value
                if bonus_rule.bonus_type == "percentage":
                    # percentage of base salary stored in breakdown isn't available here;
                    # callers should extend this if needed
                    return bonus_rule.value

        return 0.0

    async def _calculate_deduction(
        self,
        deduction_rule: DeductionRule,
        employee_id: int,
        month: int,
        year: int,
        breakdown: Dict[str, Any],
    ) -> float:
        """Calculate deduction amount based on the rule's condition."""
        if deduction_rule.condition == "absence":
            attendance = breakdown.get("attendance", {})
            absent_days = attendance.get("absent_days", 0)

            if deduction_rule.deduction_type == "per_occurrence":
                total = absent_days * deduction_rule.value
                if deduction_rule.max_deduction_per_month is not None:
                    total = min(total, deduction_rule.max_deduction_per_month)
                return total

        return 0.0

    async def _calculate_overtime(
        self,
        employee_id: int,
        month: int,
        year: int,
        overtime_rule: OvertimeRule,
        emp: Any,
    ) -> Dict[str, Any]:
        """Calculate overtime pay (timesheet integration – future phase)."""
        # TODO: Implement timesheet tracking
        return {
            "total_hours": 0.0,
            "overtime_hours": 0.0,
            "hourly_rate": 0.0,
            "multiplier": overtime_rule.multiplier,
            "total_amount": 0.0,
        }
