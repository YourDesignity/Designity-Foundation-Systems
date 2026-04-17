"""Service layer for dashboard metric aggregation."""

import logging
from datetime import date, datetime, timedelta

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class DashboardService(BaseService):
    """Dashboard metrics across HR, project, and finance domains."""

    # ====================================================================
    # DASHBOARD SUMMARY
    # ====================================================================

    async def get_dashboard_summary(self) -> dict:
        """
        Get high-level dashboard metrics.

        Returns:
            Summary metrics for employees, projects, contracts, and revenue
        """
        from backend.models import Contract, Employee, Project, Site
        from backend.services.finance.invoice_service import InvoiceService

        today = date.today()
        total_revenue = await InvoiceService().calculate_total_revenue(today.month, today.year)

        return {
            "employees": await Employee.find(Employee.status == "Active").count(),
            "projects": await Project.find_all().count(),
            "active_projects": await Project.find(Project.status == "Active").count(),
            "sites": await Site.find_all().count(),
            "contracts": await Contract.find_all().count(),
            "monthly_revenue": float(total_revenue),
        }

    async def get_hr_metrics(self) -> dict:
        """Get HR metrics including attendance and hiring activity."""
        from backend.models import Attendance, Employee

        today = date.today()
        month_start = date(today.year, today.month, 1)

        attendance_rows = await Attendance.find_all().to_list()
        monthly_rows = [row for row in attendance_rows if self._date_string_in_range(row.date, month_start, today)]
        present_rows = [row for row in monthly_rows if (row.status or "").lower() == "present"]

        employees = await Employee.find_all().to_list()
        new_hires = [
            emp
            for emp in employees
            if emp.date_of_joining and emp.date_of_joining.year == today.year and emp.date_of_joining.month == today.month
        ]

        return {
            "active_employees": len([emp for emp in employees if emp.status == "Active"]),
            "new_hires": len(new_hires),
            "attendance_records": len(monthly_rows),
            "attendance_rate": round((len(present_rows) / len(monthly_rows) * 100.0), 2) if monthly_rows else 0.0,
        }

    async def get_project_metrics(self) -> dict:
        """Get project metrics by status and contract type."""
        from backend.models import Contract, Project

        projects = await Project.find_all().to_list()
        contracts = await Contract.find_all().to_list()

        by_status: dict[str, int] = {}
        for project in projects:
            status = project.status or "Unknown"
            by_status[status] = by_status.get(status, 0) + 1

        by_contract_type: dict[str, int] = {}
        for contract in contracts:
            ctype = contract.contract_type or "Unknown"
            by_contract_type[ctype] = by_contract_type.get(ctype, 0) + 1

        return {
            "total_projects": len(projects),
            "projects_by_status": by_status,
            "total_contracts": len(contracts),
            "contracts_by_type": by_contract_type,
        }

    async def get_financial_metrics(self) -> dict:
        """Get finance metrics for dashboard cards."""
        from backend.services.finance.invoice_service import InvoiceService

        invoice_service = InvoiceService()
        today = date.today()

        monthly_revenue = await invoice_service.calculate_total_revenue(today.month, today.year)
        unpaid_invoices = await invoice_service.get_unpaid_invoices()
        overdue_invoices = await invoice_service.get_overdue_invoices()

        return {
            "monthly_revenue": float(monthly_revenue),
            "unpaid_invoices": len(unpaid_invoices),
            "overdue_invoices": len(overdue_invoices),
            "outstanding_amount": await invoice_service.calculate_outstanding_amount(),
        }

    async def get_dashboard_alerts(self) -> dict:
        """Get operational alerts (unfilled slots, overdue invoices, low stock at/below threshold)."""
        from backend.models import Material
        from backend.services.finance.invoice_service import InvoiceService
        from backend.services.role_contracts_service import RoleContractsService

        overdue_invoices = await InvoiceService().get_overdue_invoices()
        unfilled_slots = await RoleContractsService().get_unfilled_slots()
        materials = await Material.find_all().to_list()
        # Treat threshold-level stock as alert-worthy to trigger replenishment in time.
        low_stock = [row for row in materials if row.current_stock <= row.minimum_stock]

        return {
            "unfilled_slots": len(unfilled_slots),
            "overdue_invoices": len(overdue_invoices),
            "low_stock_items": len(low_stock),
            "low_stock_materials": [
                {
                    "material_id": row.uid,
                    "material_code": row.material_code,
                    "name": row.name,
                    "current_stock": row.current_stock,
                    "minimum_stock": row.minimum_stock,
                }
                for row in low_stock
            ],
        }

    async def get_attendance_trend(self, days: int = 30) -> list[dict]:
        """Get attendance trend for the last N days."""
        if days <= 0:
            self.raise_bad_request("days must be greater than zero")

        from backend.models import Attendance

        records = await Attendance.find_all().to_list()
        today = date.today()
        start = today - timedelta(days=days - 1)

        trend: list[dict] = []
        for idx in range(days):
            point = start + timedelta(days=idx)
            day_rows = [row for row in records if self._date_string_matches(row.date, point)]
            present_count = len([row for row in day_rows if (row.status or "").lower() == "present"])
            trend.append(
                {
                    "date": point.isoformat(),
                    "records": len(day_rows),
                    "present": present_count,
                    "attendance_rate": round((present_count / len(day_rows) * 100.0), 2) if day_rows else 0.0,
                }
            )

        return trend

    async def get_revenue_trend(self, months: int = 6) -> list[dict]:
        """Get revenue trend for the last N months."""
        if months <= 0:
            self.raise_bad_request("months must be greater than zero")

        from backend.services.finance.invoice_service import InvoiceService

        invoice_service = InvoiceService()
        today = date.today()
        trend: list[dict] = []

        for offset in range(months - 1, -1, -1):
            month = today.month - offset
            year = today.year
            while month <= 0:
                month += 12
                year -= 1

            amount = await invoice_service.calculate_total_revenue(month, year)
            trend.append({"month": f"{year:04d}-{month:02d}", "revenue": float(amount)})

        return trend

    # ====================================================================
    # INTERNAL HELPERS
    # ====================================================================

    @staticmethod
    def _date_string_matches(value: str | None, target: date) -> bool:
        if not value:
            return False
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return False
        return parsed == target

    @staticmethod
    def _date_string_in_range(value: str | None, start: date, end: date) -> bool:
        if not value:
            return False
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return False
        return start <= parsed <= end

    # ====================================================================
    # BACKWARD-COMPAT HELPER
    # ====================================================================

    async def get_overview_metrics(self) -> dict:
        """Backward-compatible wrapper for legacy callers."""
        return await self.get_dashboard_summary()
