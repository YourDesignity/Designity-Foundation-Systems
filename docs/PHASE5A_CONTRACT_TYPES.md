# Phase 5A – Contract Type Polymorphism System

## Overview

Phase 5A transforms the monolithic `Contract` model into a flexible,
polymorphic hierarchy.  Each contract type lives in its own class with
its own business rules, while all documents continue to be stored in
the single `contracts` MongoDB collection via **Beanie's built-in
polymorphism** (`is_root = True`).

---

## Contract Type Hierarchy

```
BaseContract  (backend/models/contracts/base_contract.py)
├── LabourContract        – fixed employees, salary = basic + allowance
├── RoleBasedContract     – role slots filled by any available employee
├── GoodsContract         – pure material / inventory supply (no employees)
└── HybridContract        – employees AND materials combined
```

---

## When to Use Each Type

| Type | Use Case | Employees? | Inventory? |
|------|----------|-----------|------------|
| `LabourContract` | Construction crew, office cleaning | ✅ Fixed names | ❌ |
| `RoleBasedContract` | Security guards, daily cleaning squads | ✅ Any matching role | ❌ |
| `GoodsContract` | Cement supply, equipment delivery | ❌ | ✅ |
| `HybridContract` | Warehouse management + material supply | ✅ Mixed | ✅ |

---

## Usage Examples

### Create a Labour Contract (fixed employees)

```python
from backend.models import LabourContract

contract = LabourContract(
    uid=1,
    contract_code="CNT-001",
    project_id=42,
    start_date="2026-05-01",
    end_date="2026-12-31",
    contract_value=50_000.0,
    assigned_employee_ids=[101, 102, 103],
)
await contract.insert()
await contract.calculate_duration()
```

### Create a Role-Based Contract

```python
from backend.models import RoleBasedContract

contract = RoleBasedContract(
    uid=2,
    contract_code="CNT-002",
    project_id=42,
    start_date="2026-05-01",
    end_date="2026-12-31",
    contract_value=30_000.0,
    role_requirements=[
        {"role": "Security Guard", "count": 5, "daily_rate": 50.0},
        {"role": "Cleaner",        "count": 3, "daily_rate": 35.0},
    ],
)
await contract.insert()
```

### Create a Goods Contract

```python
from backend.models import GoodsContract

contract = GoodsContract(
    uid=3,
    contract_code="CNT-003",
    project_id=42,
    start_date="2026-05-01",
    end_date="2026-10-31",
    contract_value=150_000.0,
    material_items=[
        {"material_id": 7, "quantity": 1000, "unit": "tons", "unit_price": 150.0}
    ],
    delivery_schedule=[
        {"date": "2026-06-01", "quantity": 200, "status": "pending"},
        {"date": "2026-07-01", "quantity": 200, "status": "pending"},
    ],
)
await contract.insert()
```

### Create a Hybrid Contract

```python
from backend.models import HybridContract

contract = HybridContract(
    uid=4,
    contract_code="CNT-004",
    project_id=42,
    start_date="2026-05-01",
    end_date="2026-12-31",
    contract_value=80_000.0,
    assigned_employee_ids=[201],           # Fixed warehouse manager
    role_requirements=[
        {"role": "Loader", "count": 5, "daily_rate": 40.0},
    ],
    material_items=[
        {"material_id": 9, "quantity": 500, "unit": "kg"},
    ],
)
await contract.insert()
```

### Polymorphic Querying

```python
from backend.models import Contract  # == BaseContract alias

# Returns ALL contract types (Labour, RoleBased, Goods, Hybrid)
# as their correct Python types
all_contracts = await Contract.find_all().to_list()

# Query only a specific type
labour_contracts = await LabourContract.find_all().to_list()
```

### Calculate Monthly Cost

```python
cost = await contract.calculate_monthly_cost(month=6, year=2026)
print(f"June cost: {cost} KWD")
```

---

## How Beanie Polymorphism Works

Beanie adds a `_type` field to every document in MongoDB when
`is_root = True` is set on the root class.  When you query via any
class in the hierarchy, Beanie reads `_type` and deserialises the
document as the correct Python type.

```
MongoDB document
{
    "_id": ObjectId("..."),
    "_type": "LabourContract",   ← added automatically by Beanie
    "uid": 1,
    "contract_code": "CNT-001",
    "assigned_employee_ids": [101, 102, 103],
    ...
}
```

Old documents without `_type` are deserialised as `BaseContract`.
Run the migration script (see below) to back-fill the discriminator.

---

## Adding a New Contract Type

1. Create `backend/models/contracts/my_new_contract.py`:

```python
from backend.models.contracts.base_contract import BaseContract
from typing import Any, Dict

class MyNewContract(BaseContract):
    # add your fields here
    custom_field: str = ""

    def __init__(self, **data):
        data.setdefault("enabled_modules", ["..."])
        data.setdefault("salary_strategy", "fixed")
        super().__init__(**data)

    async def calculate_monthly_cost(self, month: int, year: int) -> float:
        ...

    async def calculate_employee_salary(self, employee_id: int, month: int, year: int) -> float:
        ...

    async def get_required_resources(self) -> Dict[str, Any]:
        ...

    async def validate_fulfillment(self, date) -> Dict[str, Any]:
        ...
```

2. Export from `backend/models/contracts/__init__.py`.

3. Add to the `document_models` list in `backend/database.py`.

---

## Migration Guide (from old `Contract` model)

### Backward Compatibility

Existing code using `from backend.models import Contract` continues to
work.  `Contract` is now an alias for `BaseContract`, which is the
polymorphic root.  Queries like `Contract.find_all()` return all
contract types as their correct Python instances.

### Migration Script

Run the migration script to assign `_type` discriminators to legacy
documents so they are returned as the most appropriate sub-class:

```bash
# Dry-run first – inspect without writing
python -m backend.scripts.migrate_to_contract_types --dry-run

# Live migration
python -m backend.scripts.migrate_to_contract_types
```

The classification heuristic:

| Condition | Target Type |
|-----------|-------------|
| `contract_type == "Goods Supply"` | `GoodsContract` |
| `assigned_employee_ids` AND `role_slots` both present | `HybridContract` |
| `role_slots` present | `RoleBasedContract` |
| everything else | `LabourContract` |

---

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 5A | Contract type polymorphism (this PR) | ✅ Done |
| 5B | Configurable salary engine (strategy pattern) | ⏳ Planned |
| 5C | Modular workflow system (JSON-driven) | ⏳ Planned |
