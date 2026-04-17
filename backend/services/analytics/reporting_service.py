"""Service layer for cross-domain reporting."""

import csv
import io
import logging
from datetime import date
from typing import Iterable, Sequence

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ReportingService(BaseService):
    """Cross-domain report generation helpers."""

    # ====================================================================
    # MONTHLY REPORTS
    # ====================================================================

    async def generate_monthly_hr_report(self, month: int, year: int) -> dict:
        """
        Generate a monthly HR summary report.

        Args:
            month: Month number
            year: Full year

        Returns:
            HR report metrics
        """
        self._validate_month_year(month, year)

        from backend.models import Attendance, Employee

        employees = await Employee.find_all().to_list()
        attendance = await Attendance.find_all().to_list()

        monthly_rows = [row for row in attendance if self._date_string_matches_month(row.date, month, year)]
        present = len([row for row in monthly_rows if (row.status or "").lower() == "present"])
        absent = len([row for row in monthly_rows if (row.status or "").lower() != "present"])

        new_hires = [
            emp
            for emp in employees
            if emp.date_of_joining and emp.date_of_joining.month == month and emp.date_of_joining.year == year
        ]

        return {
            "month": month,
            "year": year,
            "total_employees": len(employees),
            "active_employees": len([emp for emp in employees if emp.status == "Active"]),
            "new_hires": len(new_hires),
            "attendance_records": len(monthly_rows),
            "present_days": present,
            "absent_days": absent,
            "attendance_rate": round((present / len(monthly_rows) * 100.0), 2) if monthly_rows else 0.0,
        }

    async def generate_monthly_financial_report(self, month: int, year: int) -> dict:
        """
        Generate a monthly financial summary report.

        Returns:
            Financial report dictionary
        """
        self._validate_month_year(month, year)

        from backend.services.finance.financial_analytics_service import FinancialAnalyticsService
        from backend.services.finance.invoice_service import InvoiceService

        invoice_service = InvoiceService()
        analytics_service = FinancialAnalyticsService()

        monthly_revenue = await invoice_service.calculate_total_revenue(month, year)
        outstanding_amount = await invoice_service.calculate_outstanding_amount()
        overdue_count = len(await invoice_service.get_overdue_invoices())
        pnl = await analytics_service.calculate_profit_and_loss(month, year)
        cost_breakdown = await analytics_service.calculate_cost_breakdown(month, year)

        return {
            "month": month,
            "year": year,
            "monthly_revenue": float(monthly_revenue),
            "outstanding_amount": float(outstanding_amount),
            "overdue_invoice_count": overdue_count,
            "profit_and_loss": pnl,
            "cost_breakdown": cost_breakdown,
        }

    async def generate_project_status_report(self) -> dict:
        """
        Generate a project/contract status summary report.

        Returns:
            Aggregated project and contract status metrics
        """
        from backend.models import Contract, Project, Site

        projects = await Project.find_all().to_list()
        contracts = await Contract.find_all().to_list()
        sites = await Site.find_all().to_list()

        projects_by_status: dict[str, int] = {}
        for project in projects:
            status = project.status or "Unknown"
            projects_by_status[status] = projects_by_status.get(status, 0) + 1

        contracts_by_status: dict[str, int] = {}
        for contract in contracts:
            status = contract.status or "Unknown"
            contracts_by_status[status] = contracts_by_status.get(status, 0) + 1

        expiring_soon = [
            contract
            for contract in contracts
            if contract.end_date and (contract.end_date.date() - date.today()).days <= 30 and contract.status == "Active"
        ]

        return {
            "total_projects": len(projects),
            "projects_by_status": projects_by_status,
            "total_contracts": len(contracts),
            "contracts_by_status": contracts_by_status,
            "total_sites": len(sites),
            "contracts_expiring_soon": len(expiring_soon),
        }

    # ====================================================================
    # EXPORT HELPERS
    # ====================================================================

    def export_to_csv(self, rows: Iterable[dict], columns: Sequence[str] | None = None) -> str:
        """
        Export report rows to CSV text.

        Validations:
        - rows must be iterable
        - columns default to sorted keys from all rows

        Args:
            rows: Iterable of row dictionaries
            columns: Optional ordered column names

        Returns:
            CSV content as UTF-8 text

        Notes:
            This helper builds the CSV in memory and is intended for
            dashboard/report-sized datasets.
            When `columns` is provided, extra keys in row dictionaries are
            ignored during export.
        """
        rows_list = list(rows)
        if not rows_list:
            return ""

        if columns is None:
            all_keys = set()
            for row in rows_list:
                all_keys.update(row.keys())
            columns = sorted(all_keys)

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_list)
        logger.info("CSV report exported with %s row(s)", len(rows_list))
        return buffer.getvalue()

    # ====================================================================
    # INTERNAL HELPERS
    # ====================================================================

    def _validate_month_year(self, month: int, year: int) -> None:
        if month < 1 or month > 12:
            self.raise_bad_request("month must be between 1 and 12")
        if year < 2000 or year > 2100:
            self.raise_bad_request("year is outside valid range")

    @staticmethod
    def _date_string_matches_month(value: str | None, month: int, year: int) -> bool:
        if not value:
            return False
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return False
        return parsed.month == month and parsed.year == year

    # ====================================================================
    # BACKWARD-COMPAT HELPERS
    # ====================================================================

    async def generate_headcount_report(self) -> dict:
        """Backward-compatible wrapper using current HR report data."""
        today = date.today()
        monthly = await self.generate_monthly_hr_report(today.month, today.year)
        return {
            "total": monthly["total_employees"],
            "active": monthly["active_employees"],
            "inactive": monthly["total_employees"] - monthly["active_employees"],
        }

    async def generate_contracts_report(self) -> dict:
        """Backward-compatible wrapper using current project status report data."""
        summary = await self.generate_project_status_report()
        return {
            "total": summary["total_contracts"],
            "active": summary["contracts_by_status"].get("Active", 0),
            "closed": summary["contracts_by_status"].get("Closed", 0),
        }
