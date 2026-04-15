"""
Montreal Test Data Cleanup Script
====================================
Safely clears all test data from the MongoDB database.

Usage:
    python -m backend.scripts.clear_test_data

Options (prompted interactively):
    - Clear ALL collections
    - Clear specific collections only

WARNING: NEVER run against a production database!
"""

import asyncio
import sys
from pathlib import Path

# Bootstrap path so script can be run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database import init_db, DB_NAME
from backend.models import (
    Admin, Employee, Site, Designation,
    Attendance, Overtime, Deduction,
    Vehicle, FuelLog, MaintenanceLog,
    Invoice, Conversation, Message,
    Project, Contract, EmployeeAssignment, TemporaryAssignment,
    Counter,
)

# Collections available for selective clearing.
# Display names are kept in a separate dict to avoid data-flow issues.
COLLECTION_DISPLAY_NAMES = {
    "1":  "Admins",
    "2":  "Employees",
    "3":  "Designations",
    "4":  "Projects",
    "5":  "Contracts",
    "6":  "Sites",
    "7":  "Employee Assignments",
    "8":  "Temporary Assignments",
    "9":  "Vehicles",
    "10": "Fuel Logs",
    "11": "Maintenance Logs",
    "12": "Attendance Records",
    "13": "Overtime Records",
    "14": "Deductions",
    "15": "Invoices",
    "16": "Conversations",
    "17": "Messages",
    "18": "Counters (reset IDs)",
}

COLLECTION_MODELS = {
    "1":  Admin,
    "2":  Employee,
    "3":  Designation,
    "4":  Project,
    "5":  Contract,
    "6":  Site,
    "7":  EmployeeAssignment,
    "8":  TemporaryAssignment,
    "9":  Vehicle,
    "10": FuelLog,
    "11": MaintenanceLog,
    "12": Attendance,
    "13": Overtime,
    "14": Deduction,
    "15": Invoice,
    "16": Conversation,
    "17": Message,
    "18": Counter,
}

# Safe deletion order respects foreign-key logic
ALL_IN_ORDER = [
    Message, Conversation,
    Invoice,
    Deduction, Overtime,
    Attendance,
    TemporaryAssignment, EmployeeAssignment,
    FuelLog, MaintenanceLog,
    Vehicle,
    Site,
    Contract, Project,
    Employee,
    Admin,
    Designation,
    Counter,
]


def safety_check() -> bool:
    """Refuse to run if DB_NAME looks like production."""
    db_lower = DB_NAME.lower()
    if any(kw in db_lower for kw in ("prod", "production", "live", "real")):
        print(f"\n SAFETY BLOCK: DB_NAME='{DB_NAME}' looks like PRODUCTION!")
        print("   Refusing to run. Rename your test DB or set DB_NAME env var.\n")
        return False
    return True


async def count_documents(model) -> int:
    """Return document count for a given model."""
    try:
        return await model.count()
    except Exception:
        return -1


async def clear_all() -> None:
    """Delete all records in proper dependency order."""
    for model in ALL_IN_ORDER:
        model_class_name = type(model).__name__ if not isinstance(model, type) else model.__name__
        try:
            count = await count_documents(model)
            await model.delete_all()
            print(f"   Cleared {model_class_name}: {count} records removed")
        except Exception as e:
            print(f"   Warning: Could not clear {model_class_name}: {e}")


async def clear_selected(keys: list) -> None:
    """Delete records for selected collection keys."""
    for num in keys:
        if num not in COLLECTION_DISPLAY_NAMES or num not in COLLECTION_MODELS:
            print(f"   Unknown selection: {num}")
            continue
        coll_name = COLLECTION_DISPLAY_NAMES[num]
        model = COLLECTION_MODELS[num]
        try:
            count = await count_documents(model)
            await model.delete_all()
            print(f"   Cleared {coll_name}: {count} records removed")
        except Exception as e:
            print(f"   Warning: Could not clear {coll_name}: {e}")


async def show_counts() -> None:
    """Display current document counts for all collections."""
    print()
    print("Current database state:")
    for num in sorted(COLLECTION_DISPLAY_NAMES, key=int):
        coll_name = COLLECTION_DISPLAY_NAMES[num]
        model = COLLECTION_MODELS[num]
        count = await count_documents(model)
        status = f"{count} records" if count >= 0 else "unavailable"
        print(f"   [{num:>2}] {coll_name:<30} {status}")
    print()


async def main() -> None:
    print()
    print("Montreal Test Data Cleanup Script")
    print("=" * 50)
    print()

    if not safety_check():
        sys.exit(1)

    print("Connecting to MongoDB...")
    await init_db()
    print(f"   Database: {DB_NAME}")

    await show_counts()

    print("Choose an action:")
    print("   [A] Clear ALL collections (full reset)")
    print("   [S] Clear SPECIFIC collections (choose below)")
    print("   [Q] Quit")
    print()

    choice = input("Enter choice (A/S/Q): ").strip().upper()

    if choice == "Q":
        print("Aborted.")
        return

    if choice == "A":
        confirm = input(
            "\nThis will DELETE ALL TEST DATA from the database.\n"
            f"Database: {DB_NAME}\n"
            "Are you sure? Type 'yes' to confirm: "
        ).strip().lower()
        if confirm not in ("yes", "y"):
            print("Aborted.")
            return
        print()
        print("Clearing all collections...")
        await clear_all()

    elif choice == "S":
        print()
        print("Available collections:")
        for num in sorted(COLLECTION_DISPLAY_NAMES, key=int):
            coll_name = COLLECTION_DISPLAY_NAMES[num]
            print(f"   [{num:>2}] {coll_name}")
        print()
        raw = input("Enter collection numbers to clear (comma-separated, e.g. 1,2,9): ")
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys:
            print("No collections selected. Aborted.")
            return
        confirm = input(f"Clear {len(keys)} collection(s)? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print("Aborted.")
            return
        print()
        await clear_selected(keys)

    else:
        return

    print()
    await show_counts()
    print()


if __name__ == "__main__":
    asyncio.run(main())
