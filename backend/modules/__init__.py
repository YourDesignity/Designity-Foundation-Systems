"""
Contract module system for flexible workflow management.

Modules allow contracts to enable/disable features dynamically:
- EmployeeModule: Labour management
- InventoryModule: Material tracking
- VehicleModule: Fleet operations
"""

from backend.modules.base_module import ContractModule
from backend.modules.employee_module import EmployeeModule
from backend.modules.inventory_module import InventoryModule
from backend.modules.registry import ModuleRegistry
from backend.modules.vehicle_module import VehicleModule

__all__ = [
    "ContractModule",
    "EmployeeModule",
    "InventoryModule",
    "VehicleModule",
    "ModuleRegistry",
]
