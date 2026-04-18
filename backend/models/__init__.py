"""Modular backend models package with backward-compatible re-exports."""

from backend.models.admin import (
    Admin,
    ManagerAttendance,
    ManagerAttendanceConfig,
    ManagerProfile,
)
from backend.models.assignments import DutyAssignment, EmployeeAssignment, TemporaryAssignment
from backend.models.base import Counter, MemoryNode, _coerce_date_to_datetime
from backend.models.finance import Invoice, InvoiceItem
from backend.models.hr import Attendance, Designation, Employee, Schedule, SubstituteAssignment
from backend.models.inventory import InventoryItem
from backend.models.materials import (
    Material,
    MaterialMovement,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)
from backend.models.messaging import Conversation, Message
from backend.models.payroll import Deduction, Overtime
from backend.models.projects import (
    ContractItem,
    ContractSpec,
    ContractWorkforce,
    Project,
    ProjectExpense,
    Site,
)
from backend.models.role_contracts import ContractRoleSlot, DailyRoleFulfillment, RoleFulfillmentRecord
from backend.models.settings import CompanySettings
from backend.models.vehicles import FuelLog, MaintenanceLog, TripLog, Vehicle, VehicleExpense

# Contract types (Phase 5A)
from backend.models.contracts import (
    BaseContract,
    GoodsContract,
    HybridContract,
    LabourContract,
    RoleBasedContract,
)

# Keep backward compatibility with old ``Contract`` import.
# ``BaseContract`` is the polymorphic root stored in the same
# ``contracts`` collection, so all existing query/save code
# continues to work transparently.
Contract = BaseContract

__all__ = [
    "Counter",
    "MemoryNode",
    "_coerce_date_to_datetime",
    "SubstituteAssignment",
    "Admin",
    "ManagerProfile",
    "ManagerAttendanceConfig",
    "ManagerAttendance",
    "Employee",
    "Designation",
    "Attendance",
    "Schedule",
    "Overtime",
    "Deduction",
    "DutyAssignment",
    "Vehicle",
    "TripLog",
    "VehicleExpense",
    "MaintenanceLog",
    "FuelLog",
    "ProjectExpense",
    "ContractItem",
    "ContractWorkforce",
    "ContractSpec",
    "InvoiceItem",
    "Invoice",
    "InventoryItem",
    "Material",
    "Supplier",
    "PurchaseOrderItem",
    "PurchaseOrder",
    "MaterialMovement",
    "Project",
    "ContractRoleSlot",
    "RoleFulfillmentRecord",
    "DailyRoleFulfillment",
    # Contract polymorphism (Phase 5A)
    "BaseContract",
    "LabourContract",
    "RoleBasedContract",
    "GoodsContract",
    "HybridContract",
    # Backward-compatible alias
    "Contract",
    "EmployeeAssignment",
    "TemporaryAssignment",
    "Conversation",
    "Message",
    "CompanySettings",
    "Site",
]
