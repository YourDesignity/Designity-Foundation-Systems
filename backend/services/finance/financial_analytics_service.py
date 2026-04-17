"""Service layer for financial analytics."""

from collections import Counter

from backend.services.base_service import BaseService


class FinancialAnalyticsService(BaseService):
    """Aggregated financial metrics and reports."""

    async def get_invoice_status_breakdown(self) -> dict:
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
        from datetime import datetime
        from backend.models import Invoice

        return await Invoice.find(Invoice.due_date < datetime.now(), Invoice.status != "Paid").to_list()
