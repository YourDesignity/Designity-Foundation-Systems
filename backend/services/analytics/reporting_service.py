"""Service layer for cross-domain reporting."""

from backend.services.base_service import BaseService


class ReportingService(BaseService):
    """Cross-domain report generation helpers."""

    async def generate_headcount_report(self) -> dict:
        from backend.models import Employee

        employees = await Employee.find_all().to_list()
        active = [e for e in employees if getattr(e, "status", None) == "Active"]
        return {
            "total": len(employees),
            "active": len(active),
            "inactive": len(employees) - len(active),
        }

    async def generate_contracts_report(self) -> dict:
        from backend.models import Contract

        contracts = await Contract.find_all().to_list()
        return {
            "total": len(contracts),
            "active": len([c for c in contracts if getattr(c, "status", None) == "Active"]),
            "closed": len([c for c in contracts if getattr(c, "status", None) == "Closed"]),
        }
