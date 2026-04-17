"""Backend service layer exports."""

from backend.services.base_service import BaseService
from backend.services.contract_service import ContractService
from backend.services.employee_service import EmployeeService
from backend.services.role_contracts_service import RoleContractsService
from backend.services.admin import AdminService, ManagerAttendanceService, ManagerService
from backend.services.analytics import DashboardService, ReportingService
from backend.services.assignments import AssignmentService, TemporaryAssignmentService
from backend.services.finance import FinancialAnalyticsService, InvoiceService
from backend.services.hr import AttendanceService, DesignationService, ScheduleService
from backend.services.materials import MaterialService, PurchaseOrderService, SupplierService
from backend.services.messaging import MessagingService
from backend.services.projects import ProjectService, SiteService
from backend.services.vehicles import MaintenanceService, TripLogService, VehicleService

__all__ = [
    "BaseService",
    "RoleContractsService",
    "EmployeeService",
    "ContractService",
    "AdminService",
    "ManagerService",
    "ManagerAttendanceService",
    "AttendanceService",
    "ScheduleService",
    "DesignationService",
    "ProjectService",
    "SiteService",
    "AssignmentService",
    "TemporaryAssignmentService",
    "VehicleService",
    "TripLogService",
    "MaintenanceService",
    "MaterialService",
    "SupplierService",
    "PurchaseOrderService",
    "InvoiceService",
    "FinancialAnalyticsService",
    "MessagingService",
    "DashboardService",
    "ReportingService",
]
