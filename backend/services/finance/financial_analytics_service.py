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
        """Calculate total monthly labour costs (salary + temporary labour estimate)."""
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
