# Montreal Test Data Scripts

Scripts for populating (and clearing) the Montreal database with realistic test data.

---

## Files

| File | Purpose |
|------|---------|
| `inject_test_data.py` | Creates 600+ records across all collections |
| `clear_test_data.py` | Safely removes all test data with confirmation |

---

## Quick Start

```bash
# 1. Activate virtual environment (from project root)
source .venv/bin/activate          # Linux/Mac
.venv\Scripts\activate             # Windows

# 2. Ensure MongoDB is running on localhost:27017

# 3. Install faker if not already installed
pip install faker>=24.0.0

# 4. Inject test data
python -m backend.scripts.inject_test_data

# 5. (Optional) Clear test data afterwards
python -m backend.scripts.clear_test_data
```

---

## What Gets Created

| Data Type | Count | Details |
|-----------|-------|---------|
| **Admins** | 5 | 1 SuperAdmin, 2 Admins, 2 Site Managers |
| **Employees** | 52+ | Various designations (Carpenter, Welder, etc.) |
| **Projects** | 10 | Mix of Active / Completed / On Hold |
| **Contracts** | 15-30 | 1-3 per project; some expiring soon (alerts) |
| **Sites** | 30-60 | 1-4 per contract with GPS-like addresses |
| **Employee Assignments** | 100+ | Company employees linked to active sites |
| **Temporary Assignments** | 22 | Outsourced workers on short engagements |
| **Vehicles** | 15 | Trucks, vans, SUVs with real make/model/year |
| **Fuel Logs** | 110 | Last 90 days of fill-up records |
| **Maintenance Records** | 52 | Last 12 months |
| **Attendance Records** | 200+ | Last 30 days (weekdays + some weekends) |
| **Deductions** | ~20 | Advances, fines for selected employees |
| **Invoices** | 32 | Paid / Unpaid / Overdue statuses |
| **Messages** | 55 | Broadcast conversation between admins |

---

## Default Login Credentials

All accounts use the password **`Test@123`**.

| Role | Email |
|------|-------|
| SuperAdmin | admin@montreal.com |
| Admin | john.smith@montreal.com |
| Admin | sarah.johnson@montreal.com |
| Site Manager | mike.wilson@montreal.com |
| Site Manager | emily.davis@montreal.com |

---

## Configuration

Edit the constants at the top of `inject_test_data.py` to change counts:

```python
DEFAULT_PASSWORD     = "Test@123"
NUM_EMPLOYEES        = 52
NUM_PROJECTS         = 10
NUM_VEHICLES         = 15
NUM_FUEL_LOGS        = 110
NUM_MAINTENANCE_LOGS = 52
NUM_ATTENDANCE_DAYS  = 30
NUM_INVOICES         = 32
NUM_MESSAGES         = 55
NUM_TEMP_ASSIGNMENTS = 22
```

---

## Troubleshooting

**ModuleNotFoundError: No module named 'faker'**
```bash
pip install faker>=24.0.0
```

**MongoNetworkError / Connection refused**
- Ensure MongoDB is running
- Check `backend/.env` has the correct `MONGO_URL` / `DB_HOST` settings

**DuplicateKeyError on re-run**
- The script clears all data before inserting. If a previous run failed
  mid-way, run `python -m backend.scripts.clear_test_data` first, then retry.

**AttributeError on model field**
- Run `git pull` to ensure your `models.py` is up to date.

---

## Safety

- Both scripts **refuse to run** if `DB_NAME` contains "prod", "production",
  "live", or "real"
- Both scripts prompt for confirmation before making destructive changes
- Always back up production data before any database operation

> **NEVER run these scripts against a production database!**
