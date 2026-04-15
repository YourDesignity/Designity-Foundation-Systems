#!/usr/bin/env python3
"""
migrate_to_role_slots.py
------------------------
Phase 1 Migration: Convert existing contracts to the role-based slot system.

What this script does
---------------------
1. Finds every Labour contract that has *no* role slots yet.
2. For each contract, looks at the EmployeeAssignments linked to its sites
   and creates one ContractRoleSlot per unique (designation, counter) combination.
3. Sets the default daily_rate to the company's configured external worker daily rate
   (falls back to 15.0 KWD if unset).
4. Saves the updated contract back to MongoDB.
5. Supports a --dry-run flag (default: False) to preview changes without persisting.
6. Supports a --rollback flag to strip role slots from all contracts (undo migration).

Usage
-----
    python -m backend.scripts.migrate_to_role_slots [--dry-run] [--rollback]

Requirements
------------
* MongoDB must be reachable (uses the same env config as the main app).
"""

import asyncio
import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# ── Project models ──────────────────────────────────────────────────────────
from backend.models import (
    Counter, Admin, Employee, Site, Attendance, Schedule, Designation,
    Overtime, Deduction, DutyAssignment, Vehicle, TripLog,
    MaintenanceLog, FuelLog, VehicleExpense, ContractSpec, InventoryItem,
    Invoice, Conversation, Message, ManagerProfile,
    ManagerAttendanceConfig, ManagerAttendance, CompanySettings,
    Project, Contract, ContractRoleSlot, EmployeeAssignment, TemporaryAssignment,
    Material, Supplier, PurchaseOrder, MaterialMovement,
    DailyRoleFulfillment,
)
from backend.database import get_mongo_connection_url

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("migrate_to_role_slots")

DB_NAME = "payroll_db"


# ---------------------------------------------------------------------------
# Core migration logic
# ---------------------------------------------------------------------------

async def _migrate(dry_run: bool = False) -> None:
    """Create role slots on contracts that don't have them yet."""
    # Load company default rate
    settings = await CompanySettings.find_one(CompanySettings.uid == 1)
    default_daily_rate: float = (
        settings.default_external_worker_daily_rate
        if settings and settings.default_external_worker_daily_rate
        else 15.0
    )
    log.info(f"Default daily rate: {default_daily_rate} KWD")

    # Only migrate Labour contracts without role slots
    contracts = await Contract.find(
        Contract.contract_type == "Labour"
    ).to_list()

    needs_migration = [c for c in contracts if not c.role_slots]
    log.info(f"Found {len(needs_migration)} Labour contract(s) without role slots.")

    for contract in needs_migration:
        log.info(f"Processing contract: {contract.contract_code} (uid={contract.uid})")

        # Gather assignments across all linked sites
        designation_counts: dict[str, int] = defaultdict(int)

        for site_id in contract.site_ids:
            assignments = await EmployeeAssignment.find(
                EmployeeAssignment.site_id == site_id,
                EmployeeAssignment.contract_id == contract.uid,
                EmployeeAssignment.status == "Active",
            ).to_list()

            for a in assignments:
                if a.employee_designation:
                    designation_counts[a.employee_designation] += 1

        if not designation_counts:
            log.warning(f"  → No active assignments found; creating placeholder slot 'worker_1'.")
            designation_counts["Worker"] = 1

        # Build slots
        slots: list[ContractRoleSlot] = []
        for designation, count in sorted(designation_counts.items()):
            safe_key = designation.lower().replace(" ", "_")
            for i in range(1, count + 1):
                slots.append(
                    ContractRoleSlot(
                        slot_id=f"{safe_key}_{i}",
                        designation=designation,
                        daily_rate=default_daily_rate,
                    )
                )

        log.info(f"  → Would create {len(slots)} slot(s): {[s.slot_id for s in slots]}")

        if not dry_run:
            contract.role_slots = slots
            contract.recalculate_role_summary()
            contract.updated_at = datetime.now()
            await contract.save()
            log.info(f"  ✅ Saved {len(slots)} slot(s) to contract {contract.contract_code}")
        else:
            log.info(f"  ℹ️  DRY RUN – no changes saved for {contract.contract_code}")

    log.info("Migration complete.")


async def _rollback() -> None:
    """Remove all role slots from every contract (undo migration)."""
    contracts = await Contract.find_all().to_list()
    updated = 0
    for contract in contracts:
        if contract.role_slots:
            contract.role_slots = []
            contract.total_role_slots = 0
            contract.total_daily_cost = 0.0
            contract.roles_by_designation = {}
            contract.updated_at = datetime.now()
            await contract.save()
            log.info(f"  ✅ Cleared slots from contract {contract.contract_code}")
            updated += 1
    log.info(f"Rollback complete – cleared {updated} contract(s).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(dry_run: bool, rollback: bool) -> None:
    client = AsyncIOMotorClient(get_mongo_connection_url())
    await init_beanie(
        database=client[DB_NAME],
        document_models=[
            Counter, Admin, Employee, Site, Attendance, Schedule, Designation,
            Overtime, Deduction, DutyAssignment, Vehicle, TripLog,
            MaintenanceLog, FuelLog, VehicleExpense, ContractSpec, InventoryItem,
            Invoice, Conversation, Message, ManagerProfile,
            ManagerAttendanceConfig, ManagerAttendance, CompanySettings,
            Project, Contract, EmployeeAssignment, TemporaryAssignment,
            Material, Supplier, PurchaseOrder, MaterialMovement,
            DailyRoleFulfillment,
        ],
    )

    if rollback:
        log.info("=== ROLLBACK MODE ===")
        await _rollback()
    else:
        mode = "DRY RUN" if dry_run else "LIVE"
        log.info(f"=== MIGRATION MODE [{mode}] ===")
        await _migrate(dry_run=dry_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate contracts to role-based slot system")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without persisting them",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        default=False,
        help="Remove all role slots from all contracts (undo migration)",
    )
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, rollback=args.rollback))
