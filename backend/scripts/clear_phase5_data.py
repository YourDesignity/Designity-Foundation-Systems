"""
Phase 5F: Clear Phase 5 Test Data
===================================
Safely removes ALL data created by seed_phase5_data.py.

Usage:
    python -m backend.scripts.clear_phase5_data

WARNING: NEVER run against a production database!
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Bootstrap path so script can be run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database import DB_NAME, init_db
from backend.models import (
    Admin,
    Employee,
    EmployeeAssignment,
    Material,
    MaterialMovement,
    Project,
    Site,
    Vehicle,
)
from backend.models.base import Counter
from backend.models.contracts import LabourContract, RoleBasedContract, GoodsContract, HybridContract
from backend.models.schedules import NotificationLog, RecurringSchedule, ScheduledJob
from backend.models.vehicles import TripLog
from backend.models.workflow_history import ApprovalRequest, WorkflowEvent, WorkflowHistory


# =============================================================================
# SAFETY CHECK
# =============================================================================


def safety_check() -> bool:
    """Refuse to run against production databases."""
    db_lower = DB_NAME.lower()
    if any(kw in db_lower for kw in ("prod", "production", "live", "real")):
        print(f"\n🚫 SAFETY BLOCK: DB_NAME='{DB_NAME}' looks like PRODUCTION!")
        print("   Refusing to run. Use a test database.\n")
        return False
    return True


# =============================================================================
# CLEAR ALL PHASE 5 DATA
# =============================================================================


async def clear_all_phase5_data() -> None:
    """
    Clear all Phase 5C / 5D / 5E test data from the database.

    Collections cleared (in dependency order):
    1. Phase 5E scheduling data
    2. Phase 5D workflow data
    3. Module assignment data
    4. Core entities (contracts, projects, employees, vehicles, materials)
    5. Counter reset
    """
    print("\n🗑️  Clearing Phase 5 data...\n")

    async def delete_collection(model, label: str) -> None:
        try:
            result = await model.find_all().delete()
            deleted = result.deleted_count if hasattr(result, "deleted_count") else "?"
            print(f"   ✅ {label}: {deleted} records deleted")
        except Exception as e:
            print(f"   ❌ {label}: {e}")

    # ── Phase 5E: Scheduling data ────────────────────────────────────────────
    await delete_collection(ScheduledJob, "ScheduledJob")
    await delete_collection(NotificationLog, "NotificationLog")
    await delete_collection(RecurringSchedule, "RecurringSchedule")

    # ── Phase 5D: Workflow data ──────────────────────────────────────────────
    await delete_collection(WorkflowHistory, "WorkflowHistory")
    await delete_collection(ApprovalRequest, "ApprovalRequest")
    await delete_collection(WorkflowEvent, "WorkflowEvent")

    # ── Module assignments / movements ──────────────────────────────────────
    await delete_collection(EmployeeAssignment, "EmployeeAssignment")
    await delete_collection(MaterialMovement, "MaterialMovement")
    await delete_collection(TripLog, "TripLog")
    await delete_collection(Site, "Site")

    # ── Core entities ────────────────────────────────────────────────────────
    await delete_collection(LabourContract, "LabourContract")
    await delete_collection(RoleBasedContract, "RoleBasedContract")
    await delete_collection(GoodsContract, "GoodsContract")
    await delete_collection(HybridContract, "HybridContract")
    await delete_collection(Project, "Project")
    await delete_collection(Employee, "Employee")
    await delete_collection(Vehicle, "Vehicle")
    await delete_collection(Material, "Material")
    await delete_collection(Admin, "Admin")

    # ── Counters ─────────────────────────────────────────────────────────────
    await delete_collection(Counter, "Counter")

    print("\n✅ All Phase 5 data cleared")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


async def main() -> None:
    print("=" * 60)
    print("  Phase 5F: Clear Phase 5 Test Data")
    print("=" * 60)

    if not safety_check():
        sys.exit(1)

    print(f"\n⚠️  This will DELETE all Phase 5 data from: {DB_NAME}")
    print("   Collections: contracts, projects, employees, vehicles, materials,")
    print("                sites, employee_assignments, material_movements,")
    print("                vehicle_trips, workflow_history, approval_requests,")
    print("                workflow_events, scheduled_jobs, notification_logs,")
    print("                recurring_schedules, admins, counters")

    answer = input("\n   ARE YOU SURE? [y/N]: ").strip().lower()
    if answer != "y":
        print("   Aborted.")
        sys.exit(0)

    print(f"\n🔌 Connecting to database: {DB_NAME}")
    try:
        await init_db()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

    await clear_all_phase5_data()


if __name__ == "__main__":
    asyncio.run(main())
