"""Service layer for dashboard metric aggregation."""

from backend.services.base_service import BaseService


class DashboardService(BaseService):
    """Dashboard metrics across primary domains."""

    async def get_overview_metrics(self) -> dict:
        from backend.models import Contract, Employee, Invoice, Project, Site, Vehicle

        projects = await Project.find_all().count()
        contracts = await Contract.find_all().count()
        employees = await Employee.find_all().count()
        sites = await Site.find_all().count()
        vehicles = await Vehicle.find_all().count()
        invoices = await Invoice.find_all().count()

        return {
            "projects": projects,
            "contracts": contracts,
            "employees": employees,
            "sites": sites,
            "vehicles": vehicles,
            "invoices": invoices,
        }
