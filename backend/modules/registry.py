"""Central registry of all available contract modules."""

from typing import Dict, List, Optional

from backend.modules.base_module import ContractModule
from backend.modules.employee_module import EmployeeModule
from backend.modules.inventory_module import InventoryModule
from backend.modules.vehicle_module import VehicleModule


class ModuleRegistry:
    """
    Central registry of all available contract modules.
    Provides access to module instances and metadata.
    """

    _modules: Dict[str, ContractModule] = {
        "employee": EmployeeModule(),
        "inventory": InventoryModule(),
        "vehicle": VehicleModule(),
    }

    @classmethod
    def get_module(cls, name: str) -> Optional[ContractModule]:
        """Get a module instance by name."""
        return cls._modules.get(name)

    @classmethod
    def list_modules(cls) -> List[str]:
        """List all available module names."""
        return list(cls._modules.keys())

    @classmethod
    def get_module_info(cls, name: str) -> Optional[Dict]:
        """Get metadata about a module."""
        module = cls._modules.get(name)
        if not module:
            return None

        return {
            "name": module.module_name,
            "required_models": module.required_models,
            "description": module.__doc__.strip() if module.__doc__ else "",
        }

    @classmethod
    def list_all_modules_info(cls) -> List[Dict]:
        """Get metadata for all modules."""
        return [
            cls.get_module_info(name)
            for name in cls.list_modules()
        ]

    @classmethod
    def register_module(cls, module: ContractModule) -> None:
        """Register a new module dynamically."""
        cls._modules[module.module_name] = module

    @classmethod
    def unregister_module(cls, name: str) -> None:
        """Unregister a module."""
        if name in cls._modules:
            del cls._modules[name]
