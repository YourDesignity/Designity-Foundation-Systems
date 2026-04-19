# Phase 5C — Modular Contract Workflow System

## Overview

Phase 5C introduces a **plugin-based module system** that allows contracts to
enable and disable features dynamically.  Each module encapsulates a distinct
business concern (employees, inventory, vehicles, …) and exposes a consistent
interface for cost calculation and validation.

---

## Architecture

```
Contract (Base)
    ↓ enabled_modules: ["employee", "inventory", "vehicle"]
    ├── EmployeeModule   — labour management
    ├── InventoryModule  — material tracking
    └── VehicleModule    — fleet operations
```

Contracts store the list of active modules in `enabled_modules` and any
module-specific configuration in `module_config`.

---

## File Layout

```
backend/
└── modules/
    ├── __init__.py          # Package exports
    ├── base_module.py       # Abstract base class (ContractModule)
    ├── employee_module.py   # EmployeeModule
    ├── inventory_module.py  # InventoryModule
    ├── vehicle_module.py    # VehicleModule
    └── registry.py          # ModuleRegistry
```

---

## Abstract Base Class — `ContractModule`

Every module must subclass `ContractModule` and implement three abstract
methods:

| Method | Purpose |
|---|---|
| `initialize(contract)` | Called when the module is enabled for a contract.  Returns setup metadata. |
| `calculate_cost(contract, month, year)` | Returns the module's cost contribution for the given calendar month. |
| `validate(contract, date)` | Validates the module's requirements for a specific date. |

Two optional overrides are also available:

| Method | Purpose |
|---|---|
| `get_resource_requirements(contract)` | Declare what resources this contract needs. |
| `cleanup(contract)` | Tear-down when the module is disabled. |

---

## Core Modules

### EmployeeModule

**module_name:** `"employee"`

Manages fixed employee assignments to a contract.

- **`initialize`** — counts currently assigned employees via `EmployeeAssignment`.
- **`calculate_cost`** — sums `basic_salary + allowance` for every assigned
  employee.
- **`validate`** — checks `Attendance` records for the target date and reports
  absent employees.

### InventoryModule

**module_name:** `"inventory"`

Tracks material/inventory movements for a contract.

- **`initialize`** — counts material movements linked to the contract
  (`reference_id == contract.uid`, `reference_type == "contract_usage"`).
- **`calculate_cost`** — sums `total_cost` of all `OUT` movements in the given
  month.
- **`validate`** — reports how many movements occurred on the target date.

### VehicleModule

**module_name:** `"vehicle"`

Tracks fleet usage and expenses for a contract.

- **`initialize`** — counts trip logs linked via `specs["contract_uid"]`.
- **`calculate_cost`** — sums vehicle expenses and computes trip distance
  statistics.
- **`validate`** — counts trips scheduled on the target date.

> **Note:** The current `TripLog` and `VehicleExpense` models do not carry a
> dedicated `contract_id` column.  Until a migration adds that column, the
> vehicle module uses `specs["contract_uid"]` as a convention.  The structure
> is in place and cost calculations will populate automatically once the
> migration runs.

---

## ModuleRegistry

`ModuleRegistry` is a class-level dictionary of module instances keyed by
`module_name`.

```python
from backend.modules import ModuleRegistry

# List all available modules
ModuleRegistry.list_modules()
# → ["employee", "inventory", "vehicle"]

# Get a single module
module = ModuleRegistry.get_module("employee")

# Get metadata
ModuleRegistry.get_module_info("employee")
# → {"name": "employee", "required_models": [...], "description": "..."}

# Register a custom module at runtime
ModuleRegistry.register_module(my_custom_module)

# Remove a module
ModuleRegistry.unregister_module("my_custom")
```

---

## Database Changes

Two new fields were added to the `Contract` document in
`backend/models/projects.py`:

```python
enabled_modules: List[str] = []  # ["employee", "inventory", "vehicle"]
module_config: Dict[str, Any] = {}  # module-specific settings
```

No migration is required — Beanie/MongoDB handles schemaless additions
gracefully.

---

## Creating a Custom Module

```python
from backend.modules.base_module import ContractModule
from backend.modules.registry import ModuleRegistry
from typing import Any, Dict


class DeliveryModule(ContractModule):
    """Module for tracking goods delivery for contracts."""

    module_name = "delivery"
    required_models = ["DeliveryOrder"]

    async def initialize(self, contract: Any) -> Dict[str, Any]:
        return {"module": self.module_name, "status": "initialized"}

    async def calculate_cost(
        self, contract: Any, month: int, year: int
    ) -> Dict[str, Any]:
        # ... query DeliveryOrder, sum costs ...
        return {"module": self.module_name, "total_cost": 0.0}

    async def validate(self, contract: Any, date: Any) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_valid": True,
            "issues": [],
            "warnings": [],
        }


# Register at startup
ModuleRegistry.register_module(DeliveryModule())
```

---

## Usage Example

```python
from backend.modules import ModuleRegistry

contract = await Contract.find_one(Contract.uid == contract_id)

# Enable modules on a contract
contract.enabled_modules = ["employee", "inventory"]
await contract.save()

# Calculate costs for April 2026
for module_name in contract.enabled_modules:
    module = ModuleRegistry.get_module(module_name)
    if module:
        cost = await module.calculate_cost(contract, month=4, year=2026)
        print(cost)

# Validate for today
from datetime import date
for module_name in contract.enabled_modules:
    module = ModuleRegistry.get_module(module_name)
    if module:
        result = await module.validate(contract, date.today())
        if not result["is_valid"]:
            print(f"Issues in {module_name}:", result["issues"])
```

---

## Expected Outcomes

| # | Outcome |
|---|---|
| 1 | Modular architecture implemented |
| 2 | 3 core modules working (Employee, Inventory, Vehicle) |
| 3 | Module registry functional (register/unregister at runtime) |
| 4 | Contracts carry `enabled_modules` and `module_config` fields |
| 5 | Cost calculations delegated to modules |
| 6 | Validation delegated to modules |
| 7 | Foundation ready for Phase 5D (workflow engine) |
