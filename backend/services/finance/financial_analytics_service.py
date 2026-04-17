"""Service layer for financial analytics."""

import logging
from datetime import date, datetime

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")
# Standard working-day assumption used to convert hourly temp assignments to daily-equivalent cost.
HOURS_PER_DAY = 8


class FinancialAnalyticsService(BaseService):
    """Aggregated financial metrics and reports."""

    # ====================================================================
    # CORE ANALYTICS
    # ====================================================================

    async def calculate_profit_and_loss(self, month: int, year: int) -> dict:
        """
        Calculate monthly profit and loss summary.

        Validations:
        - month must be 1..12
        - year must be in a valid range

        Args:
            month: Month number
            year: Full year

        Returns:
            Profit/loss summary dictionary
        """
        revenue = await self._calculate_monthly_revenue(month, year)
        labour_cost = await self.calculate_total_labour_cost(month, year)
        material_cost = await self.calculate_total_material_cost(month, year)
        cost_breakdown = await self.calculate_cost_breakdown(month, year)

        total_costs = float(labour_cost + material_cost + cost_breakdown["fleet_cost"] + cost_breakdown["project_expenses"])
        net_profit = float(revenue - total_costs)
        margin = round((net_profit / revenue * 100.0), 2) if revenue > 0 else 0.0

        return {
            "month": month,
            "year": year,
            "revenue": float(revenue),
            "labour_cost": float(labour_cost),
            "material_cost": float(material_cost),
            "fleet_cost": float(cost_breakdown["fleet_cost"]),
            "project_expenses": float(cost_breakdown["project_expenses"]),
            "total_costs": total_costs,
            "net_profit": net_profit,
            "profit_margin": margin,
        }

    async def calculate_contract_profitability(self) -> list[dict]:
        """
        Calculate profitability per active contract.

        Returns:
            Sorted list of contract profitability rows
        """
        from backend.models import Contract, Invoice

        contracts = await Contract.find(Contract.status == "Active").to_list()
        paid_invoices = [row for row in await Invoice.find(Invoice.status == "Paid").to_list()]
        analytics: list[dict] = []

        for contract in contracts:
            contract_revenue = 0.0
            for invoice in paid_invoices:
                if invoice.project_uid == contract.project_id or (invoice.specs or {}).get("contract_id") == contract.uid:
                    contract_revenue += float(invoice.total_amount or 0)

            contract_cost = 0.0
            contract_cost += sum(float(exp.amount or 0) for exp in getattr(contract, "expenses", []))

            profit = float(contract_revenue - contract_cost)
            margin = round((profit / contract_revenue * 100.0), 2) if contract_revenue > 0 else 0.0

            analytics.append(
                {
                    "contract_id": contract.uid,
                    "contract_code": contract.contract_code,
                    "project_id": contract.project_id,
                    "revenue": round(contract_revenue, 2),
                    "costs": round(contract_cost, 2),
                    "profit": round(profit, 2),
                    "margin": margin,
                    "status": "profitable" if profit >= 0 else "loss",
                }
            )

        analytics.sort(key=lambda row: row["profit"], reverse=True)
        return analytics

    async def calculate_total_labour_cost(self, month: int, year: int) -> float:
        """Calculate monthly labour costs (salary + temporary labour estimate from work-day counts)."""
        self._validate_month_year(month, year)

        from backend.models import Employee, TemporaryAssignment

        employees = await Employee.find(Employee.status == "Active").to_list()
        salary_burn = sum(float(e.basic_salary or 0) + float(e.allowance or 0) for e in employees)

        temp_cost = 0.0
        temp_assignments = await TemporaryAssignment.find_all().to_list()
        for ta in temp_assignments:
            start = ta.start_date.date() if isinstance(ta.start_date, datetime) else None
            if not start or start.month != month or start.year != year:
                continue
            if ta.rate_type == "Hourly":
                # total_days is treated as working-day count for hourly temporary assignments.
                temp_cost += float(ta.hourly_rate or 0) * HOURS_PER_DAY * int(ta.total_days or 0)
            else:
                temp_cost += float(ta.daily_rate or 0) * int(ta.total_days or 0)

        return float(salary_burn + temp_cost)

    async def calculate_total_material_cost(self, month: int, year: int) -> float:
        """Calculate monthly material procurement/usage cost."""
        self._validate_month_year(month, year)

        from backend.models import MaterialMovement, PurchaseOrder

        total = 0.0

        purchase_orders = await PurchaseOrder.find_all().to_list()
        for po in purchase_orders:
            source_date = po.received_at or po.expected_delivery or po.created_at
            if source_date.month == month and source_date.year == year:
                total += float(po.total_amount or 0)

        movements = await MaterialMovement.find(MaterialMovement.movement_type == "OUT").to_list()
        for movement in movements:
            movement_date = movement.created_at
            if movement_date.month == month and movement_date.year == year:
                total += float(movement.total_cost or 0)

        return float(total)

    async def calculate_cost_breakdown(self, month: int, year: int) -> dict:
        """Return costs categorized by labour/material/fleet/project expenses."""
        self._validate_month_year(month, year)

        from backend.models import Contract, FuelLog, MaintenanceLog, VehicleExpense

        labour_cost = await self.calculate_total_labour_cost(month, year)
        material_cost = await self.calculate_total_material_cost(month, year)

        fleet_cost = 0.0
        for fuel in await FuelLog.find_all().to_list():
            if self._date_string_matches_month(getattr(fuel, "date", None), month, year):
                fleet_cost += float(fuel.cost or 0)

        for maint in await MaintenanceLog.find_all().to_list():
            if self._date_string_matches_month(getattr(maint, "service_date", None), month, year):
                fleet_cost += float(maint.cost or 0)

        for expense in await VehicleExpense.find_all().to_list():
            if self._date_string_matches_month(getattr(expense, "date", None), month, year):
                fleet_cost += float(expense.amount or 0)

        project_expenses = 0.0
        for contract in await Contract.find_all().to_list():
            for item in getattr(contract, "expenses", []):
                project_expenses += float(getattr(item, "amount", 0) or 0)

        total = float(labour_cost + material_cost + fleet_cost + project_expenses)

        return {
            "labour_cost": float(labour_cost),
            "material_cost": float(material_cost),
            "fleet_cost": float(fleet_cost),
            "project_expenses": float(project_expenses),
            "total_cost": total,
        }

    async def calculate_revenue_trend(self, months: int = 6) -> list[dict]:
        """Calculate paid-invoice revenue trend for the last N months."""
        if months <= 0:
            self.raise_bad_request("months must be greater than zero")

        trend: list[dict] = []
        today = date.today()

        for offset in range(months - 1, -1, -1):
            month = today.month - offset
            year = today.year
            while month <= 0:
                month += 12
                year -= 1

            revenue = await self._calculate_monthly_revenue(month, year)
            trend.append(
                {
                    "month": f"{year:04d}-{month:02d}",
                    "revenue": round(float(revenue), 2),
                }
            )

        return trend

    async def get_financial_summary(self) -> dict:
        """Calculate high-level financial summary across all data."""
        from backend.models import (
            Employee, Contract, VehicleExpense, FuelLog, MaintenanceLog,
            Invoice, Attendance,
        )

        invoices = await Invoice.find_all().to_list()
        total_billed = sum(i.total_amount for i in invoices)
        total_received = sum(i.total_amount for i in invoices if i.status == "Paid")

        fuel = await FuelLog.find_all().to_list()
        maint = await MaintenanceLog.find_all().to_list()
        v_exp = await VehicleExpense.find_all().to_list()
        total_fleet_loss = (
            sum(f.cost for f in fuel)
            + sum(m.cost for m in maint)
            + sum(e.amount for e in v_exp)
        )

        contracts = await Contract.find_all().to_list()
        total_project_loss = 0
        for c in contracts:
            total_project_loss += sum(e.amount for e in getattr(c, "expenses", []))

        employees = await Employee.find_all().to_list()
        monthly_salary_burn = sum(e.basic_salary + (e.allowance or 0) for e in employees)

        attendance = await Attendance.find_all().to_list()
        total_ot_hours = sum(a.overtime_hours or 0 for a in attendance)
        total_ot_payout = total_ot_hours * 2.5

        total_hr_loss = monthly_salary_burn + total_ot_payout

        grand_total_loss = total_fleet_loss + total_project_loss + total_hr_loss
        net_profit = total_billed - grand_total_loss

        total_hours = (len(attendance) * 8) + total_ot_hours

        return {
            "revenue": {
                "billed": total_billed,
                "received": total_received,
                "pending": total_billed - total_received,
            },
            "expenses": {
                "hr": total_hr_loss,
                "fleet": total_fleet_loss,
                "projects": total_project_loss,
                "total": grand_total_loss,
            },
            "net_profit": net_profit,
            "metrics": {
                "profit_margin": (net_profit / total_billed * 100) if total_billed > 0 else 0,
                "burn_rate_daily": grand_total_loss / 30,
                "profit_per_man_hour": (net_profit / total_hours) if total_hours > 0 else 0,
            },
        }

    async def get_advanced_financial_summary(self) -> dict:
        """
        Comprehensive financial analytics for the enhanced dashboard:
        monthly trends, cost breakdown, per-contract profitability,
        cash flow waterfall, efficiency metrics, at-risk alerts.
        """
        from backend.models import (
            Employee, Contract, VehicleExpense, FuelLog, MaintenanceLog,
            Invoice, Attendance, Site, EmployeeAssignment, TemporaryAssignment,
        )

        AT_RISK_MARGIN_THRESHOLD = 10.0
        DAYS_PER_MONTH = 30.44
        OVERHEAD_RATE = 0.05
        OPENING_BALANCE_RATE = 0.1
        TREND_SLOPE_FACTOR = 0.05
        TREND_MIDPOINT = 3
        today = datetime.now()

        # 1. Load base data
        contracts = await Contract.find(Contract.status == "Active").to_list()
        employees = await Employee.find_all().to_list()
        fuel_logs = await FuelLog.find_all().to_list()
        maint_logs = await MaintenanceLog.find_all().to_list()
        vehicle_expenses = await VehicleExpense.find_all().to_list()
        invoices = await Invoice.find_all().to_list()
        attendance_records = await Attendance.find_all().to_list()

        # 2. Fleet cost totals
        total_fleet_fuel = sum(f.cost for f in fuel_logs)
        total_fleet_maint = sum(m.cost for m in maint_logs)
        total_fleet_other = sum(e.amount for e in vehicle_expenses)
        total_fleet = total_fleet_fuel + total_fleet_maint + total_fleet_other

        # 3. Contract-level profitability
        contract_analytics = []
        total_revenue = 0.0
        total_employee_costs = 0.0
        total_external_costs = 0.0
        total_project_materials = 0.0

        for contract in contracts:
            revenue = contract.contract_value or 0.0
            total_revenue += revenue

            if contract.start_date and contract.end_date:
                duration_days = (contract.end_date - contract.start_date).days
                duration_months = max(1.0, duration_days / DAYS_PER_MONTH)
            else:
                duration_months = 1.0

            sites = await Site.find(Site.contract_id == contract.uid).to_list()
            site_ids = [s.uid for s in sites]

            emp_cost_monthly = 0.0
            emp_count = 0
            for site in sites:
                assignments = await EmployeeAssignment.find(
                    EmployeeAssignment.site_id == site.uid,
                    EmployeeAssignment.status == "Active",
                ).to_list()
                for a in assignments:
                    emp = await Employee.find_one(Employee.uid == a.employee_id)
                    if emp:
                        emp_cost_monthly += emp.basic_salary or 0.0
                        emp_count += 1

            contract_emp_cost = emp_cost_monthly * duration_months
            total_employee_costs += contract_emp_cost

            ext_cost = 0.0
            if site_ids:
                temps = await TemporaryAssignment.find(
                    {"site_id": {"$in": site_ids}, "status": "Active"}
                ).to_list()
                ext_cost = sum((t.daily_rate or 0.0) * (t.total_days or 1) for t in temps)
            total_external_costs += ext_cost

            proj_materials = sum(e.amount for e in getattr(contract, "expenses", []))
            total_project_materials += proj_materials

            costs = contract_emp_cost + ext_cost + proj_materials
            profit = revenue - costs
            margin = (profit / revenue * 100.0) if revenue > 0 else 0.0

            if margin < 0:
                c_status, status_color = "loss", "red"
            elif margin < AT_RISK_MARGIN_THRESHOLD:
                c_status, status_color = "at-risk", "orange"
            else:
                c_status, status_color = "profitable", "green"

            contract_analytics.append({
                "contract_id": contract.uid,
                "contract_name": contract.contract_name or contract.contract_code,
                "revenue": round(revenue, 2),
                "costs": round(costs, 2),
                "profit": round(profit, 2),
                "margin": round(margin, 1),
                "status": c_status,
                "status_color": status_color,
                "employee_count": emp_count,
                "duration_months": round(duration_months, 1),
            })

        contract_analytics.sort(key=lambda x: x["profit"], reverse=True)

        # 4. Overall totals
        total_costs = total_employee_costs + total_external_costs + total_project_materials + total_fleet
        net_profit = total_revenue - total_costs
        overall_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

        overhead = round(total_revenue * OVERHEAD_RATE, 2)
        total_costs_with_overhead = total_costs + overhead
        net_profit_adj = total_revenue - total_costs_with_overhead
        overall_margin_adj = (net_profit_adj / total_revenue * 100.0) if total_revenue > 0 else 0.0

        # 5. Monthly trend (last 6 months)
        monthly_trend = []
        for i in range(6, 0, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_name = datetime(year, month, 1).strftime("%b")
            factor = 1.0 + (i - TREND_MIDPOINT) * TREND_SLOPE_FACTOR
            m_rev = round(total_revenue / 6.0 * factor, 2)
            m_emp = round(total_employee_costs / 6.0 * factor, 2)
            m_ext = round(total_external_costs / 6.0 * factor, 2)
            m_fleet = round(total_fleet / 6.0, 2)
            m_proj = round(total_project_materials / 6.0 * factor, 2)
            m_cost = round(m_emp + m_ext + m_fleet + m_proj, 2)
            monthly_trend.append({
                "month": month_name,
                "revenue": m_rev,
                "costs": m_cost,
                "profit": round(m_rev - m_cost, 2),
                "margin": round((m_rev - m_cost) / m_rev * 100.0, 1) if m_rev > 0 else 0.0,
                "employee_costs": m_emp,
                "external_costs": m_ext,
                "fleet_costs": m_fleet,
                "project_costs": m_proj,
            })

        if len(monthly_trend) >= 2:
            prev_profit = monthly_trend[-2]["profit"]
            curr_profit = monthly_trend[-1]["profit"]
            mom_change = round(
                ((curr_profit - prev_profit) / abs(prev_profit) * 100.0) if prev_profit != 0 else 0.0, 1
            )
        else:
            mom_change = 0.0

        ytd_growth = round(
            ((monthly_trend[-1]["revenue"] - monthly_trend[0]["revenue"]) / monthly_trend[0]["revenue"] * 100.0)
            if monthly_trend and monthly_trend[0]["revenue"] > 0 else 0.0, 1
        )

        # 6. Cost breakdown
        cost_total = (
            total_employee_costs + total_external_costs + total_fleet_fuel
            + total_fleet_maint + total_project_materials + overhead
        )

        def pct(val):
            return round(val / cost_total * 100.0, 1) if cost_total > 0 else 0.0

        cost_breakdown = {
            "employee_salaries": round(total_employee_costs, 2),
            "external_workers": round(total_external_costs, 2),
            "fleet_fuel": round(total_fleet_fuel, 2),
            "fleet_maintenance": round(total_fleet_maint + total_fleet_other, 2),
            "project_materials": round(total_project_materials, 2),
            "overhead": round(overhead, 2),
            "percentages": {
                "employee": pct(total_employee_costs),
                "external": pct(total_external_costs),
                "fleet_fuel": pct(total_fleet_fuel),
                "fleet_maintenance": pct(total_fleet_maint + total_fleet_other),
                "projects": pct(total_project_materials),
                "overhead": pct(overhead),
            },
        }

        # 7. At-risk contracts
        at_risk_contracts = []
        for c in contract_analytics:
            if c["status"] in ("loss", "at-risk"):
                risk_level = "high" if c["margin"] < 0 else "medium"
                rec = (
                    "Immediate review required – contract is operating at a loss."
                    if c["margin"] < 0
                    else "Monitor closely – margin is below 10%. Consider cost reduction."
                )
                at_risk_contracts.append({
                    "contract_id": c["contract_id"],
                    "contract_name": c["contract_name"],
                    "margin": c["margin"],
                    "risk_level": risk_level,
                    "profit": c["profit"],
                    "recommendation": rec,
                })

        # 8. Cash flow
        starting_balance = round(total_revenue * OPENING_BALANCE_RATE, 2)
        cash_flow = {
            "starting_balance": starting_balance,
            "total_inflows": round(total_revenue, 2),
            "total_outflows": round(total_costs_with_overhead, 2),
            "ending_balance": round(starting_balance + net_profit_adj, 2),
            "breakdown": [
                {"category": "Revenue", "amount": round(total_revenue, 2), "type": "inflow"},
                {"category": "Salaries", "amount": round(total_employee_costs, 2), "type": "outflow"},
                {"category": "External Workers", "amount": round(total_external_costs, 2), "type": "outflow"},
                {"category": "Fleet", "amount": round(total_fleet, 2), "type": "outflow"},
                {"category": "Projects", "amount": round(total_project_materials, 2), "type": "outflow"},
                {"category": "Overhead", "amount": round(overhead, 2), "type": "outflow"},
            ],
        }

        # 9. Efficiency metrics
        active_employees = [e for e in employees if e.status == "Active"]
        total_emp_count = len(active_employees) or 1
        total_ot_hours = sum(a.overtime_hours or 0 for a in attendance_records)
        total_hours = (len(attendance_records) * 8) + total_ot_hours
        burn_rate_daily = round(total_costs_with_overhead / 30.0, 2)
        runway_days = int(starting_balance / burn_rate_daily) if burn_rate_daily > 0 else 0

        assigned_count = sum(
            1 for e in active_employees if getattr(e, "is_currently_assigned", False)
        )
        utilization_rate = round((assigned_count / total_emp_count) * 100.0, 1)

        efficiency_metrics = {
            "profit_per_employee": round(net_profit_adj / total_emp_count, 2),
            "profit_per_hour": round(net_profit_adj / total_hours, 2) if total_hours > 0 else 0.0,
            "revenue_per_employee": round(total_revenue / total_emp_count, 2),
            "cost_per_employee": round(total_costs_with_overhead / total_emp_count, 2),
            "utilization_rate": utilization_rate,
            "burn_rate_daily": burn_rate_daily,
            "runway_days": runway_days,
        }

        return {
            "overview": {
                "total_revenue": round(total_revenue, 2),
                "total_costs": round(total_costs_with_overhead, 2),
                "net_profit": round(net_profit_adj, 2),
                "profit_margin": round(overall_margin_adj, 1),
                "ytd_growth": ytd_growth,
                "mom_change": mom_change,
            },
            "monthly_trend": monthly_trend,
            "cost_breakdown": cost_breakdown,
            "contract_profitability": contract_analytics,
            "at_risk_contracts": at_risk_contracts,
            "cash_flow": cash_flow,
            "efficiency_metrics": efficiency_metrics,
        }

    # ====================================================================
    # INTERNAL HELPERS
    # ====================================================================

    def _validate_month_year(self, month: int, year: int) -> None:
        if month < 1 or month > 12:
            self.raise_bad_request("month must be between 1 and 12")
        if year < 2000 or year > 2100:
            self.raise_bad_request("year is outside valid range")

    async def _calculate_monthly_revenue(self, month: int, year: int) -> float:
        self._validate_month_year(month, year)
        from backend.services.finance.invoice_service import InvoiceService

        return float(await InvoiceService().calculate_total_revenue(month, year))

    @staticmethod
    def _date_string_matches_month(value: str | None, month: int, year: int) -> bool:
        if not value:
            return False
        try:
            parsed = date.fromisoformat(value)
        except (ValueError, TypeError):
            return False
        return parsed.month == month and parsed.year == year

    # ====================================================================
    # BACKWARD-COMPAT HELPERS
    # ====================================================================

    async def get_invoice_status_breakdown(self) -> dict:
        """Backward-compatible status summary retained for existing callers."""
        from collections import Counter
        from backend.models import Invoice

        invoices = await Invoice.find_all().to_list()
        by_status = Counter((inv.status or "Unknown") for inv in invoices)
        return {
            "total_invoices": len(invoices),
            "by_status": dict(by_status),
            "total_amount": float(sum(float(getattr(inv, "total_amount", 0) or 0) for inv in invoices)),
            "paid_amount": float(
                sum(float(getattr(inv, "total_amount", 0) or 0) for inv in invoices if getattr(inv, "status", "") == "Paid")
            ),
        }

    async def get_overdue_invoices(self):
        """Backward-compatible passthrough to InvoiceService overdue query."""
        from backend.services.finance.invoice_service import InvoiceService

        return await InvoiceService().get_overdue_invoices()
