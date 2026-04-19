# Database Seeding Scripts

Seed scripts that populate the database with realistic test data covering all
Modules, Workflow, and Scheduling
features.

---

## Files

| File | Purpose |
|------|---------|
| `seed_database.py` | Creates 700+ records across all collections |
| `clear_database.py` | Safely removes all test data with confirmation |

---

## Quick Start

```bash
# 1. Activate virtual environment (from project root)
source .venv/bin/activate          # Linux/Mac
.venv\Scripts\activate             # Windows

# 2. Ensure MongoDB is running on localhost:27017

# 3. Install dependencies if needed
pip install faker>=24.0.0 passlib[bcrypt]

# 4. Seed database
python -m backend.scripts.seed_database

# 5. (Optional) Clear database data afterwards
python -m backend.scripts.clear_database
```

---

## Default Login Credentials

All accounts use the password **`Test@123`**.

| Role | Email |
|------|-------|
| SuperAdmin | superadmin@designity.com |
| Admin | alice.morgan@designity.com |
| Admin | bob.chen@designity.com |
| Admin | carol.hayes@designity.com |
| Site Manager | david.park@designity.com |
| Site Manager | emma.lewis@designity.com |
| Site Manager | frank.torres@designity.com |
| Site Manager | grace.kim@designity.com |

---

## What Gets Created

| Data Type | Count | Details |
|-----------|-------|---------|
| **Admins** | 8 | 1 SuperAdmin, 3 Admins, 4 Site Managers |
| **Projects** | 15 | Various statuses, 2-3 contracts each |
| **Contracts** | 35 | 5 DRAFT, 5 PENDING_APPROVAL, 15 ACTIVE, 5 COMPLETED, 5 CANCELLED |
| **Employees** | 60 | 50 Active, 10 Inactive; various designations |
| **Vehicles** | 20 | Pickups, Vans, SUVs, Heavy Equipment |
| **Materials** | 40 | Steel, Concrete, Wood, Tools, Safety Equipment, etc. |
| **Sites** | ~20 | One per ACTIVE/COMPLETED contract with employee module |
| **Employee Assignments** | 80–150 | Employees linked to ACTIVE/COMPLETED contracts |
| **Material Movements** | 100–200 | Inventory usage records linked to contracts |
| **Vehicle Trips** | 20–60 | Trip logs linked to contracts via `specs.contract_uid` |
| **Workflow History** | 100+ | State transitions for all contracts |
| **Approval Requests** | 18+ | PENDING (5), APPROVED (10), REJECTED (3) |
| **Scheduled Jobs** | 80–120 | PENDING, COMPLETED, FAILED mix |
| **Notification Logs** | 80–120 | SENT and FAILED notifications |
| **Recurring Schedules** | 3 | Monthly automated jobs |
| **Workflow Events** | 15–20 | Event audit log |

---

## Contract Distribution

### By Workflow State

| State | Count | Notes |
|-------|-------|-------|
| `DRAFT` | 5 | Not started; future start dates |
| `PENDING_APPROVAL` | 5 | Submitted for review; future start dates |
| `ACTIVE` | 15 | Currently running; some expiring soon |
| `COMPLETED` | 5 | Ended 1–90 days ago |
| `CANCELLED` | 5 | Terminated early |

### By Date Scenario

| Scenario | Count |
|----------|-------|
| Future start (10–30 days) | 5+ |
| Currently active (started 30–180 days ago) | 10 |
| Expiring soon (7, 15, 25, 32, 45 days) | 5 |
| Already completed (ended 1–90 days ago) | 5 |
| Cancelled | 5 |

### Module Distribution (ACTIVE/COMPLETED contracts)

| Modules | Approximate % |
|---------|--------------|
| Employee only | ~40% |
| Inventory only | ~20% |
| Vehicle only | ~10% |
| Employee + Inventory | ~10% |
| Employee + Vehicle | ~10% |
| All three | ~10% |

---

## Scheduled Jobs

| Job Type | Status | Trigger |
|----------|--------|---------|
| `contract_activation` | PENDING | Future-start DRAFT contracts |
| `contract_expiry_warning_30` | PENDING/COMPLETED | 30 days before end_date |
| `contract_expiry_warning_15` | PENDING/COMPLETED | 15 days before end_date |
| `contract_expiry_warning_7` | PENDING/COMPLETED | 7 days before end_date |
| `contract_auto_completion` | PENDING | On end_date |
| `renewal_request` | PENDING/COMPLETED | 60 days before end_date |
| `monthly_cost_calculation` | PENDING | 2026-05-01 01:00 UTC |
| `contract_activation` | FAILED | Cancelled contracts (retry exhausted) |

---

## Notification Log Types

| Type | Channel | Notes |
|------|---------|-------|
| `expiry_warning` | email, in_app | For contracts expiring ≤ 45 days |
| `renewal_reminder` | email | For contracts needing renewal |
| `payment_reminder` | email | Monthly payment reminders |
| `contract_completed` | email | Auto-completion notifications |
| `expiry_warning` | sms | FAILED (non-existent recipient) |

---

## Troubleshooting

**ModuleNotFoundError: No module named 'faker'**
```bash
pip install faker>=24.0.0
```

**MongoNetworkError / Connection refused**
- Ensure MongoDB is running on `localhost:27017`
- Check `backend/.env` for `MONGO_URL` / `DB_HOST` settings

**DuplicateKeyError on re-run**
- A previous run may have partially seeded data. Run the cleanup script first:
  ```bash
  python -m backend.scripts.clear_database
  ```
  Then retry seeding.

**AttributeError on model field**
- Run `git pull` to ensure your models are up to date.
- `BaseContract` must have `workflow_state`, `workflow_metadata`, `module_config`,
  `state_changed_at`, `state_changed_by` fields.

---

## Safety

- Both scripts **refuse to run** if `DB_NAME` contains "prod", "production",
  "live", or "real"
- Both scripts prompt for **confirmation** before making destructive changes
- Always back up production data before any database operation

> **NEVER run these scripts against a production database!**

---

## Sample MongoDB Queries

```javascript
// Count contracts by workflow state
db.contracts.aggregate([
  { $group: { _id: "$workflow_state", count: { $sum: 1 } } }
])

// Find all ACTIVE contracts with employee module
db.contracts.find({
  workflow_state: "ACTIVE",
  enabled_modules: "employee"
})

// Get pending scheduled jobs
db.scheduled_jobs.find({ status: "PENDING" }).sort({ scheduled_for: 1 })

// Get recent workflow history for a contract
db.workflow_history.find({ contract_id: 1 }).sort({ timestamp: -1 })

// Check pending approval requests
db.approval_requests.find({ status: "PENDING" })

// Count notification logs by status
db.notification_logs.aggregate([
  { $group: { _id: "$status", count: { $sum: 1 } } }
])
```
