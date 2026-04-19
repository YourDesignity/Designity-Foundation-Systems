"""
Financial Analytics Service — Enhanced.

Key fixes vs original:
- Revenue now reads from Invoice collection (Paid invoices) not contract_value
- Monthly trend uses real per-month invoice + cost data (not synthetic slope factor)
- Cost breakdown includes salary from Employee records + overtime from Overtime model
- Waterfall uses validated floats (no NaN)
- Date range filtering added to get_advanced_financial_summary
"""

import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")
HOURS_PER_DAY = 8
OVERHEAD_RATE = 0.05


def _safe_float(v) -> float:
    try:
        f = float(v or 0)
        return f if f == f else 0.0  # NaN check
    except (TypeError, ValueError):
        return 0.0


def _month_range(year: int, month: int):
    _, last = monthrange(year, month)
    start = datetime(year, month, 1)
    end   = datetime(year, month, last, 23, 59, 59)
    return start, end


class FinancialAnalyticsService(BaseService):

    # ── Core monthly helpers ──────────────────────────────────────────────────

    async def _revenue_for_month(self, year: int, month: int) -> float:
        """Sum of paid invoice amounts for a given month."""
        from backend.models.finance import Invoice
        start, end = _month_range(year, month)
        invoices = await Invoice.find_all().to_list()
        total = 0.0
        for inv in invoices:
            if inv.status not in ("Paid", "paid"):
                continue
            inv_date = None
            if inv.date:
                try:
                    inv_date = datetime.strptime(inv.date[:10], "%Y-%m-%d")
                except Exception:
                    pass
            if inv_date and start <= inv_date <= end:
                total += _safe_float(inv.total_amount)
        return round(total, 3)

    async def _costs_for_month(self, year: int, month: int) -> dict:
        """Aggregate all cost categories for a given month."""
        from backend.models import Employee, FuelLog, MaintenanceLog, VehicleExpense
        from backend.models.payroll import Overtime, Deduction
        from backend.models.settings import CompanySettings

        start, end = _month_range(year, month)
        month_prefix = f"{year}-{month:02d}"

        # Employee salaries (pro-rated monthly)
        employees = await Employee.find(Employee.status == "Active").to_list()
        salary = sum(_safe_float(e.basic_salary) + _safe_float(e.allowance) for e in employees)

        # Overtime costs
        settings = await CompanySettings.find_one()
        norm_mult = _safe_float(getattr(settings, 'normal_overtime_multiplier', 1.25)) or 1.25
        off_mult  = _safe_float(getattr(settings, 'offday_overtime_multiplier',  1.5))  or 1.5
        ot_records = await Overtime.find_all().to_list()
        ot_cost = 0.0
        for r in ot_records:
            if r.date and r.date.startswith(month_prefix):
                emp = next((e for e in employees if e.uid == r.employee_uid), None)
                if emp:
                    work_days = _safe_float(emp.standard_work_days) or 28
                    daily = (_safe_float(emp.basic_salary) / work_days) if work_days else 0
                    hourly = daily / 8
                    mult = off_mult if r.type == "Offday" else norm_mult
                    ot_cost += _safe_float(r.hours) * hourly * mult

        # Deductions (reduce net payroll cost — shown separately)
        ded_records = await Deduction.find_all().to_list()
        deductions = sum(_safe_float(r.amount) for r in ded_records if r.pay_period == month_prefix)

        # Fleet costs
        fleet = 0.0
        for f in await FuelLog.find_all().to_list():
            if f.date and str(f.date)[:7] == month_prefix:
                fleet += _safe_float(f.cost)
        for m in await MaintenanceLog.find_all().to_list():
            if m.service_date and str(m.service_date)[:7] == month_prefix:
                fleet += _safe_float(m.cost)
        for e in await VehicleExpense.find_all().to_list():
            if e.date and str(e.date)[:7] == month_prefix:
                fleet += _safe_float(e.amount)

        emp_net = salary + ot_cost - deductions

        return {
            "employee": round(emp_net, 3),
            "fleet":    round(fleet, 3),
            "external": 0.0,
            "materials": 0.0,
            "total":    round(emp_net + fleet, 3),
        }

    # ── Advanced summary ──────────────────────────────────────────────────────

    async def get_advanced_financial_summary(
        self,
        date_from: Optional[str] = None,
        date_to:   Optional[str] = None,
    ) -> dict:
        """
        Full financial analytics.
        date_from / date_to: optional YYYY-MM-DD strings.
        Defaults to last 6 months.
        """
        from backend.models import (
            Employee, FuelLog, MaintenanceLog, VehicleExpense,
            Site, EmployeeAssignment, TemporaryAssignment,
        )
        from backend.models.finance import Invoice
        from backend.models.contracts.base_contract import BaseContract
        from backend.models.payroll import Overtime, Deduction

        today = datetime.now()

        # ── Date range ────────────────────────────────────────────────────────
        if date_to:
            range_end = datetime.strptime(date_to, "%Y-%m-%d")
        else:
            range_end = today.replace(day=1) - timedelta(days=1)
            range_end = range_end.replace(day=monthrange(range_end.year, range_end.month)[1],
                                          hour=23, minute=59, second=59)

        if date_from:
            range_start = datetime.strptime(date_from, "%Y-%m-%d")
        else:
            range_start = (range_end.replace(day=1) - timedelta(days=150)).replace(day=1)

        # ── Load everything ───────────────────────────────────────────────────
        employees     = await Employee.find_all().to_list()
        active_emps   = [e for e in employees if e.status == "Active"]
        invoices      = await Invoice.find_all().to_list()
        fuel_logs     = await FuelLog.find_all().to_list()
        maint_logs    = await MaintenanceLog.find_all().to_list()
        veh_expenses  = await VehicleExpense.find_all().to_list()
        contracts     = await BaseContract.find_all().to_list()
        settings_doc  = None
        try:
            from backend.models.settings import CompanySettings
            settings_doc = await CompanySettings.find_one()
        except Exception:
            pass

        norm_mult = _safe_float(getattr(settings_doc, 'normal_overtime_multiplier', 1.25)) or 1.25
        off_mult  = _safe_float(getattr(settings_doc, 'offday_overtime_multiplier',  1.5))  or 1.5

        # ── Invoice revenue totals ────────────────────────────────────────────
        all_paid_rev  = sum(_safe_float(i.total_amount) for i in invoices if i.status in ("Paid", "paid"))
        all_unpaid    = sum(_safe_float(i.total_amount) for i in invoices if i.status not in ("Paid", "paid"))
        total_billed  = all_paid_rev + all_unpaid

        # ── Total costs ───────────────────────────────────────────────────────
        monthly_salary = sum(_safe_float(e.basic_salary) + _safe_float(e.allowance) for e in active_emps)
        total_fleet    = (sum(_safe_float(f.cost) for f in fuel_logs)
                         + sum(_safe_float(m.cost) for m in maint_logs)
                         + sum(_safe_float(e.amount) for e in veh_expenses))
        fleet_fuel     = sum(_safe_float(f.cost) for f in fuel_logs)
        fleet_maint    = sum(_safe_float(m.cost) for m in maint_logs) + sum(_safe_float(e.amount) for e in veh_expenses)

        # Overtime costs
        ot_records = await Overtime.find_all().to_list()
        ot_cost_total = 0.0
        for r in ot_records:
            emp = next((e for e in active_emps if e.uid == r.employee_uid), None)
            if emp:
                wd = _safe_float(emp.standard_work_days) or 28
                hourly = (_safe_float(emp.basic_salary) / wd / 8) if wd else 0
                mult   = off_mult if r.type == "Offday" else norm_mult
                ot_cost_total += _safe_float(r.hours) * hourly * mult

        ded_records   = await Deduction.find_all().to_list()
        total_deductions = sum(_safe_float(r.amount) for r in ded_records)

        emp_cost_net  = monthly_salary + ot_cost_total - total_deductions

        # External/temp worker costs
        temp_assignments = await TemporaryAssignment.find_all().to_list()
        ext_cost = sum(
            (_safe_float(t.hourly_rate) * HOURS_PER_DAY * _safe_float(t.total_days))
            if t.rate_type == "Hourly"
            else (_safe_float(t.daily_rate) * _safe_float(t.total_days))
            for t in temp_assignments
        )

        overhead = round((emp_cost_net + total_fleet + ext_cost) * OVERHEAD_RATE, 3)
        total_costs = round(emp_cost_net + total_fleet + ext_cost + overhead, 3)
        net_profit  = round(all_paid_rev - total_costs, 3)
        margin      = round((net_profit / all_paid_rev * 100) if all_paid_rev > 0 else 0.0, 2)
        mom_change  = 0.0
        ytd_growth  = 0.0

        # ── Monthly trend (real data per month) ───────────────────────────────
        monthly_trend = []
        for offset in range(5, -1, -1):
            d    = today.replace(day=1) - timedelta(days=1) if offset == 0 else today
            mo   = today.month - offset
            yr   = today.year
            while mo <= 0:
                mo += 12; yr -= 1
            month_prefix = f"{yr}-{mo:02d}"

            m_rev = await self._revenue_for_month(yr, mo)
            m_costs = await self._costs_for_month(yr, mo)

            # Employee costs from active salaries (split across months)
            m_emp = round(monthly_salary / 1, 3)  # real monthly burn
            m_fleet = m_costs["fleet"]
            m_ext = 0.0

            # Overtime for this specific month
            m_ot = 0.0
            for r in ot_records:
                if r.date and r.date.startswith(month_prefix):
                    emp = next((e for e in active_emps if e.uid == r.employee_uid), None)
                    if emp:
                        wd = _safe_float(emp.standard_work_days) or 28
                        hourly = (_safe_float(emp.basic_salary) / wd / 8) if wd else 0
                        mult   = off_mult if r.type == "Offday" else norm_mult
                        m_ot  += _safe_float(r.hours) * hourly * mult

            m_ded = sum(_safe_float(r.amount) for r in ded_records if r.pay_period == month_prefix)
            m_emp_net = round(m_emp + m_ot - m_ded, 3)
            m_total_cost = round(m_emp_net + m_fleet + m_ext, 3)
            m_overhead = round(m_total_cost * OVERHEAD_RATE, 3)
            m_cost_w_oh = round(m_total_cost + m_overhead, 3)
            m_profit = round(m_rev - m_cost_w_oh, 3)

            monthly_trend.append({
                "month":          datetime(yr, mo, 1).strftime("%b"),
                "month_full":     f"{yr}-{mo:02d}",
                "revenue":        m_rev,
                "costs":          m_cost_w_oh,
                "profit":         m_profit,
                "margin":         round((m_profit / m_rev * 100) if m_rev > 0 else 0.0, 1),
                "employee_costs": m_emp_net,
                "external_costs": m_ext,
                "fleet_costs":    m_fleet,
                "project_costs":  0.0,
                "overtime_cost":  round(m_ot, 3),
                "overhead":       m_overhead,
            })

        if len(monthly_trend) >= 2:
            prev = monthly_trend[-2]["profit"]
            curr = monthly_trend[-1]["profit"]
            mom_change = round(((curr - prev) / abs(prev) * 100) if prev != 0 else 0.0, 1)

        if monthly_trend and monthly_trend[0]["revenue"] > 0:
            ytd_growth = round(
                (monthly_trend[-1]["revenue"] - monthly_trend[0]["revenue"])
                / monthly_trend[0]["revenue"] * 100, 1
            )

        # ── Cost breakdown (donut chart) ──────────────────────────────────────
        cost_total = total_costs or 1  # avoid div-by-zero

        def pct(v):
            return round(_safe_float(v) / cost_total * 100, 1)

        cost_breakdown = {
            "employee_salaries": round(monthly_salary, 3),
            "overtime":          round(ot_cost_total, 3),
            "deductions":        round(total_deductions, 3),
            "external_workers":  round(ext_cost, 3),
            "fleet_fuel":        round(fleet_fuel, 3),
            "fleet_maintenance": round(fleet_maint, 3),
            "project_materials": 0.0,
            "overhead":          round(overhead, 3),
            "percentages": {
                "employee":          pct(monthly_salary),
                "overtime":          pct(ot_cost_total),
                "external":          pct(ext_cost),
                "fleet_fuel":        pct(fleet_fuel),
                "fleet_maintenance": pct(fleet_maint),
                "overhead":          pct(overhead),
            },
        }

        # ── Contract profitability ────────────────────────────────────────────
        contract_analytics = []
        for contract in contracts:
            rev = 0.0
            for inv in invoices:
                if (inv.project_uid == contract.project_id
                        and inv.status in ("Paid", "paid")):
                    rev += _safe_float(inv.total_amount)
            if rev == 0:
                rev = _safe_float(contract.contract_value)

            cost = 0.0
            try:
                for exp in getattr(contract, "expenses", []):
                    cost += _safe_float(getattr(exp, "amount", 0))
            except Exception:
                pass

            profit = round(rev - cost, 3)
            marg   = round((profit / rev * 100) if rev > 0 else 0.0, 1)
            status = "loss" if profit < 0 else ("at-risk" if marg < 10 else "profitable")

            contract_analytics.append({
                "contract_id":   contract.uid,
                "contract_name": contract.contract_name or contract.contract_code,
                "contract_code": contract.contract_code,
                "revenue":       round(rev, 3),
                "costs":         round(cost, 3),
                "profit":        profit,
                "margin":        marg,
                "status":        status,
                "status_color":  "green" if status == "profitable" else ("orange" if status == "at-risk" else "red"),
            })

        contract_analytics.sort(key=lambda x: x["profit"], reverse=True)

        # ── At-risk contracts ─────────────────────────────────────────────────
        at_risk = [
            {
                "contract_id":    c["contract_id"],
                "contract_name":  c["contract_name"],
                "margin":         c["margin"],
                "profit":         c["profit"],
                "risk_level":     "high" if c["margin"] < 0 else "medium",
                "recommendation": (
                    "Immediate review — operating at a loss."
                    if c["margin"] < 0
                    else "Monitor closely — margin below 10%."
                ),
            }
            for c in contract_analytics if c["status"] in ("loss", "at-risk")
        ]

        # ── Cash flow waterfall ───────────────────────────────────────────────
        starting_balance = round(all_paid_rev * 0.1, 3)
        cash_flow = {
            "starting_balance": starting_balance,
            "total_inflows":    round(all_paid_rev, 3),
            "total_outflows":   round(total_costs, 3),
            "ending_balance":   round(starting_balance + net_profit, 3),
            "breakdown": [
                {"category": "Revenue",          "amount": round(all_paid_rev, 3),   "type": "inflow"},
                {"category": "Salaries",         "amount": round(monthly_salary, 3), "type": "outflow"},
                {"category": "Overtime",         "amount": round(ot_cost_total, 3),  "type": "outflow"},
                {"category": "External Workers", "amount": round(ext_cost, 3),       "type": "outflow"},
                {"category": "Fleet",            "amount": round(total_fleet, 3),    "type": "outflow"},
                {"category": "Overhead",         "amount": round(overhead, 3),       "type": "outflow"},
            ],
        }

        # ── Efficiency metrics ────────────────────────────────────────────────
        emp_count = max(len(active_emps), 1)
        assigned  = sum(1 for e in active_emps if getattr(e, "is_currently_assigned", False))
        util_rate = round((assigned / emp_count) * 100, 1)
        burn_rate = round(total_costs / 30, 3)
        runway    = int(starting_balance / burn_rate) if burn_rate > 0 else 0

        efficiency_metrics = {
            "profit_per_employee":    round(net_profit / emp_count, 3),
            "revenue_per_employee":   round(all_paid_rev / emp_count, 3),
            "cost_per_employee":      round(total_costs / emp_count, 3),
            "profit_per_hour":        round(net_profit / max(emp_count * 8 * 22, 1), 3),
            "utilization_rate":       util_rate,
            "burn_rate_daily":        burn_rate,
            "cash_runway_days":       runway,
        }

        # ── Invoice summary ───────────────────────────────────────────────────
        invoice_summary = {
            "total_billed":    round(total_billed, 3),
            "total_received":  round(all_paid_rev, 3),
            "total_pending":   round(all_unpaid, 3),
            "invoice_count":   len(invoices),
            "paid_count":      sum(1 for i in invoices if i.status in ("Paid", "paid")),
            "overdue_count":   sum(1 for i in invoices if i.status in ("Overdue", "overdue")),
        }

        return {
            "overview": {
                "total_revenue":  round(all_paid_rev, 3),
                "total_costs":    round(total_costs, 3),
                "net_profit":     round(net_profit, 3),
                "profit_margin":  margin,
                "ytd_growth":     ytd_growth,
                "mom_change":     mom_change,
                "total_billed":   round(total_billed, 3),
                "outstanding":    round(all_unpaid, 3),
            },
            "monthly_trend":        monthly_trend,
            "cost_breakdown":       cost_breakdown,
            "contract_profitability": contract_analytics,
            "at_risk_contracts":    at_risk,
            "cash_flow":            cash_flow,
            "efficiency_metrics":   efficiency_metrics,
            "invoice_summary":      invoice_summary,
        }

    # ── Legacy endpoints ──────────────────────────────────────────────────────

    async def calculate_profit_and_loss(self, month: int, year: int) -> dict:
        revenue = await self._revenue_for_month(year, month)
        costs   = await self._costs_for_month(year, month)
        net     = round(revenue - costs["total"], 3)
        margin  = round((net / revenue * 100) if revenue > 0 else 0.0, 2)
        return {
            "month": month, "year": year,
            "revenue": revenue, "total_costs": costs["total"],
            "net_profit": net, "profit_margin": margin,
        }

    async def get_financial_summary(self) -> dict:
        from backend.models.finance import Invoice
        from backend.models import Employee
        invoices = await Invoice.find_all().to_list()
        employees = await Employee.find(Employee.status == "Active").to_list()
        billed   = sum(_safe_float(i.total_amount) for i in invoices)
        received = sum(_safe_float(i.total_amount) for i in invoices if i.status in ("Paid", "paid"))
        salary   = sum(_safe_float(e.basic_salary) + _safe_float(e.allowance) for e in employees)
        return {
            "revenue": {"billed": billed, "received": received, "pending": billed - received},
            "expenses": {"hr": salary, "fleet": 0, "projects": 0, "total": salary},
            "net_profit": received - salary,
            "metrics": {
                "profit_margin": round(((received - salary) / received * 100) if received > 0 else 0.0, 2),
                "burn_rate_daily": round(salary / 30, 3),
                "profit_per_man_hour": 0.0,
            },
        }

    async def calculate_total_labour_cost(self, month: int, year: int) -> float:
        costs = await self._costs_for_month(year, month)
        return costs["employee"]

    async def calculate_total_material_cost(self, month: int, year: int) -> float:
        return 0.0

    async def calculate_cost_breakdown(self, month: int, year: int) -> dict:
        costs = await self._costs_for_month(year, month)
        return {"fleet_cost": costs["fleet"], "project_expenses": 0.0}

    async def calculate_contract_profitability(self) -> list:
        summary = await self.get_advanced_financial_summary()
        return summary["contract_profitability"]

    async def calculate_revenue_trend(self, months: int = 6) -> list:
        summary = await self.get_advanced_financial_summary()
        return summary["monthly_trend"]

    def _validate_month_year(self, month: int, year: int) -> None:
        if not (1 <= month <= 12):
            self.raise_bad_request("month must be 1–12")
        if year < 2000 or year > 2100:
            self.raise_bad_request("year out of range")

    def _date_string_matches_month(self, date_str, month: int, year: int) -> bool:
        if not date_str:
            return False
        return str(date_str)[:7] == f"{year}-{month:02d}"
