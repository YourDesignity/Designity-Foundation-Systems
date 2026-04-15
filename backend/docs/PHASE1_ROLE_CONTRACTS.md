# Phase 1: Role-Based Labour Contracts

## Overview

Labour contracts in Montreal International Management define **fixed role slots** (e.g. 5 Drivers, 10 Cleaners) that must be staffed every working day. Rather than assigning specific employees to a contract for its entire duration, site managers record **which employee filled each slot on a given day**. This allows different employees to cover the same role on different days (due to sick leave, rotation, etc.) while still tracking attendance, cost, and shortages accurately.

---

## Data Model Relationships

```
Project (1)
  └─ Contract (many)           ← contract_type="Labour"
       ├─ ContractRoleSlot[]   ← embedded in Contract document
       └─ DailyRoleFulfillment (many)   ← one per (contract_id, date)
            └─ RoleFulfillmentRecord[]  ← one per slot per day
```

### ContractRoleSlot *(embedded BaseModel)*

Defines a **permanent slot** in a contract. Slots are immutable during the contract period.

| Field | Type | Description |
|---|---|---|
| `slot_id` | str | Unique ID within the contract, e.g. `driver_1` |
| `designation` | str | Role name, e.g. `Driver`, `Cleaner` |
| `daily_rate` | float | KWD per day (must be > 0) |
| `current_employee_id` | int? | Employee currently filling this slot |
| `current_employee_name` | str? | Denormalised name for display |
| `assigned_since` | datetime? | When current assignment started |

### DailyRoleFulfillment *(MongoDB Document)*

One document per `(contract_id, date)` pair. Captures who showed up on that day.

| Field | Type | Description |
|---|---|---|
| `uid` | int | Auto-increment ID |
| `contract_id` | int | Links to `Contract.uid` |
| `site_id` | int | Links to `Site.uid` |
| `date` | datetime | Work day (stored as midnight UTC) |
| `role_fulfillments` | List[RoleFulfillmentRecord] | One record per slot |
| `total_roles_required` | int | Count of slots |
| `total_roles_filled` | int | Count of filled slots |
| `total_daily_cost` | float | Sum of `cost_applied` across all records |
| `unfilled_slots` | List[str] | `slot_id`s with `is_filled=False` |
| `shortage_cost_impact` | float | Revenue lost from unfilled slots |
| `recorded_by_manager_id` | int | Manager who submitted the record |

### RoleFulfillmentRecord *(embedded BaseModel)*

| Field | Type | Description |
|---|---|---|
| `slot_id` | str | Matches a `ContractRoleSlot.slot_id` |
| `designation` | str | Role for validation |
| `daily_rate` | float | Snapshot of rate at recording time |
| `employee_id` | int? | Employee who worked |
| `employee_name` | str? | |
| `is_filled` | bool | Whether slot was staffed |
| `attendance_status` | str | `Present` \| `Absent` \| `Leave` \| `Late` |
| `replacement_employee_id` | int? | Swap audit trail |
| `replacement_employee_name` | str? | |
| `replacement_reason` | str? | |
| `cost_applied` | float | Actual KWD cost for the day |
| `payment_status` | str | `Pending` \| `Paid` |
| `notes` | str? | Free-text |

### Contract *(updated)*

New fields added to the existing `Contract` document:

| Field | Type | Default | Description |
|---|---|---|---|
| `contract_type` | str | `"Labour"` | `"Labour"` \| `"Goods Supply"` \| `"Equipment Rental"` |
| `role_slots` | List[ContractRoleSlot] | `[]` | Slot definitions |
| `total_daily_cost` | float | `0.0` | Auto-calculated from slot rates |
| `total_role_slots` | int | `0` | Auto-calculated count |
| `roles_by_designation` | Dict[str, int] | `{}` | e.g. `{"Driver": 5, "Cleaner": 10}` |

---

## API Reference

### Contract Role Slots

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/contract-roles/configure` | Define/replace all role slots | Admin/SuperAdmin |
| `GET` | `/contract-roles/{contract_id}` | Get role configuration | Any |
| `PUT` | `/contract-roles/{contract_id}/slots` | Add or update slots | Admin/SuperAdmin |
| `DELETE` | `/contract-roles/{contract_id}/slots/{slot_id}` | Remove a slot | Admin/SuperAdmin |

#### Example: Configure role slots

```http
POST /contract-roles/configure
Authorization: Bearer <token>
Content-Type: application/json

{
  "contract_id": 42,
  "slots": [
    {"slot_id": "driver_1", "designation": "Driver", "daily_rate": 25.0},
    {"slot_id": "driver_2", "designation": "Driver", "daily_rate": 25.0},
    {"slot_id": "cleaner_1", "designation": "Cleaner", "daily_rate": 18.0},
    {"slot_id": "cleaner_2", "designation": "Cleaner", "daily_rate": 18.0},
    {"slot_id": "cleaner_3", "designation": "Cleaner", "daily_rate": 18.0}
  ]
}
```

---

### Daily Role Fulfillment

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/daily-fulfillment/record` | Record daily fulfillment | Any |
| `GET` | `/daily-fulfillment/{contract_id}/date/{date}` | Get a specific day's record | Any |
| `PUT` | `/daily-fulfillment/{fulfillment_id}/assign` | Assign employee to slot | Any |
| `PUT` | `/daily-fulfillment/{fulfillment_id}/swap` | Swap employee in slot | Any |
| `GET` | `/daily-fulfillment/{contract_id}/month/{month}/year/{year}` | Monthly cost report | Any |
| `GET` | `/daily-fulfillment/unfilled` | All unfilled slots (alerts) | Any |

#### Example: Record daily fulfillment

```http
POST /daily-fulfillment/record
Authorization: Bearer <token>
Content-Type: application/json

{
  "contract_id": 42,
  "site_id": 7,
  "date": "2026-04-15",
  "recorded_by_manager_id": 5,
  "role_fulfillments": [
    {
      "slot_id": "driver_1",
      "designation": "Driver",
      "daily_rate": 25.0,
      "employee_id": 101,
      "employee_name": "Ahmed Al-Rashid",
      "is_filled": true,
      "attendance_status": "Present",
      "cost_applied": 25.0,
      "payment_status": "Pending"
    },
    {
      "slot_id": "driver_2",
      "designation": "Driver",
      "daily_rate": 25.0,
      "is_filled": false,
      "attendance_status": "Absent",
      "cost_applied": 0.0,
      "payment_status": "Pending"
    }
  ]
}
```

#### Example: Monthly cost report response

```json
{
  "contract_id": 42,
  "month": 4,
  "year": 2026,
  "total_days_recorded": 22,
  "total_roles_required": 110,
  "total_roles_filled": 98,
  "total_cost": 2450.0,
  "shortage_cost_impact": 300.0,
  "fulfillment_rate": 0.8909,
  "cost_by_designation": {
    "Driver": 1100.0,
    "Cleaner": 1350.0
  },
  "daily_breakdown": [
    {
      "date": "2026-04-01",
      "total_required": 5,
      "total_filled": 4,
      "total_cost": 118.0,
      "shortage_cost_impact": 25.0,
      "unfilled_slots": ["driver_2"]
    }
  ]
}
```

---

## Cost Calculation Formulas

### Daily Cost

```
total_daily_cost = Σ cost_applied for each RoleFulfillmentRecord
cost_applied      = daily_rate  (if is_filled=True)
                  = 0.0         (if is_filled=False)
```

### Monthly Cost

```
monthly_cost = Σ total_daily_cost for each DailyRoleFulfillment in the month
```

### Shortage Cost Impact

```
shortage_cost_impact = Σ daily_rate for each unfilled slot
```

### Fulfillment Rate

```
fulfillment_rate = total_roles_filled / total_roles_required  (0.0 – 1.0)
```

---

## Validation Rules

1. **Slot ID uniqueness** – slot IDs must be unique within a contract.
2. **Daily rate > 0** – zero or negative rates are rejected.
3. **Designation match** – the employee's `designation` must equal the slot's `designation`.
4. **No double-booking** – the same employee cannot fill more than one slot on the same day.
5. **No future dates** – fulfillment records cannot be created for future dates.
6. **Manager site access** – Site Managers can only record fulfillment for their assigned sites.
7. **No duplicate records** – only one fulfillment record per `(contract_id, date)` pair.

---

## Migration

To convert existing contracts to the role-based system:

```bash
# Preview (no DB writes)
python -m backend.scripts.migrate_to_role_slots --dry-run

# Live migration
python -m backend.scripts.migrate_to_role_slots

# Rollback (remove all role slots)
python -m backend.scripts.migrate_to_role_slots --rollback
```

The migration script:
1. Finds Labour contracts without role slots.
2. Inspects active `EmployeeAssignment` records for each contract's sites.
3. Creates one slot per assigned employee (using their designation).
4. Uses the company's configured `default_external_worker_daily_rate` as the daily rate.
5. Falls back to 15.0 KWD if no company setting exists.

---

## Security

| Operation | Required Role |
|---|---|
| Configure/update/delete role slots | `Admin` or `SuperAdmin` |
| Record daily fulfillment | `Site Manager` (own sites only), `Admin`, `SuperAdmin` |
| Read any data | Any authenticated user |

---

## Performance Notes

- `DailyRoleFulfillment` is indexed on `(contract_id, date)` and `(site_id, date)` for fast monthly queries.
- `Contract.role_slots` is embedded (not a separate collection), so role configuration reads are O(1).
- Monthly aggregation is done in Python after a single indexed MongoDB query.
