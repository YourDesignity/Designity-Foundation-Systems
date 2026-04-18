"""
Migration script to convert existing contracts to typed contracts.

This script inspects documents in the ``contracts`` collection and
re-saves them as the appropriate sub-class (LabourContract,
RoleBasedContract, GoodsContract, HybridContract) so that the Beanie
``_type`` discriminator is written to MongoDB.

Usage
-----
Dry-run (inspect only, no writes)::

    python -m backend.scripts.migrate_to_contract_types --dry-run

Live run::

    python -m backend.scripts.migrate_to_contract_types

Notes
-----
* Documents that already have a ``_type`` field are skipped.
* The classification heuristic mirrors the legacy ``contract_type``
  field and the presence of ``assigned_employee_ids`` / ``role_slots``:

  - ``contract_type == "Goods Supply"``  → GoodsContract
  - ``assigned_employee_ids`` AND ``role_slots``/``role_requirements``
    present  → HybridContract
  - ``role_slots`` present (role-based)  → RoleBasedContract
  - everything else  → LabourContract (default)

  Full, rule-based classification will be implemented in Phase 5B once
  the salary system is ready.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from backend.database import get_mongo_connection_url
from backend.models import (
    Counter, Admin, Employee, Site, Attendance, Schedule, Designation,
    Overtime, Deduction, DutyAssignment, Vehicle, TripLog,
    MaintenanceLog, FuelLog, VehicleExpense, ContractSpec, InventoryItem,
    Invoice, Conversation, Message, ManagerProfile,
    ManagerAttendanceConfig, ManagerAttendance, CompanySettings,
    Project, EmployeeAssignment, TemporaryAssignment,
    Material, Supplier, PurchaseOrder, MaterialMovement,
    DailyRoleFulfillment,
)
from backend.models.contracts import (
    LabourContract,
    RoleBasedContract,
    GoodsContract,
    HybridContract,
)

load_dotenv(dotenv_path=Path("./backend/.env"))

DB_NAME = "payroll_db"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("migrate_to_contract_types")


def _classify(doc: dict) -> str:
    """Return the target contract type name for a raw MongoDB document."""
    contract_type = doc.get("contract_type", "Labour")
    has_employees = bool(doc.get("assigned_employee_ids"))
    has_roles = bool(doc.get("role_slots") or doc.get("role_requirements"))

    if contract_type == "Goods Supply":
        return "GoodsContract"
    if has_employees and has_roles:
        return "HybridContract"
    if has_roles:
        return "RoleBasedContract"
    return "LabourContract"


_TYPE_MAP = {
    "LabourContract": LabourContract,
    "RoleBasedContract": RoleBasedContract,
    "GoodsContract": GoodsContract,
    "HybridContract": HybridContract,
}


async def migrate_contracts(dry_run: bool = False) -> None:
    """
    Convert existing Contract documents to specific contract types.

    Strategy:
    1. Find all contracts without a ``_type`` discriminator.
    2. Classify each document using the heuristic in :func:`_classify`.
    3. Re-save via the appropriate sub-class so Beanie writes ``_type``.
    """
    client = AsyncIOMotorClient(get_mongo_connection_url())
    await init_beanie(
        database=client[DB_NAME],
        document_models=[
            Counter, Admin, Employee, Site, Attendance, Schedule, Designation,
            Overtime, Deduction, DutyAssignment, Vehicle, TripLog,
            MaintenanceLog, FuelLog, VehicleExpense, ContractSpec, InventoryItem,
            Invoice, Conversation, Message, ManagerProfile,
            ManagerAttendanceConfig, ManagerAttendance, CompanySettings,
            Project, EmployeeAssignment, TemporaryAssignment,
            Material, Supplier, PurchaseOrder, MaterialMovement,
            DailyRoleFulfillment,
            LabourContract,
            RoleBasedContract,
            GoodsContract,
            HybridContract,
        ],
    )

    collection = client[DB_NAME]["contracts"]
    untyped = await collection.find({"_type": {"$exists": False}}).to_list(None)

    log.info("Found %d untyped contract document(s).", len(untyped))

    stats: dict[str, int] = {k: 0 for k in _TYPE_MAP}
    skipped = 0

    for raw in untyped:
        target_name = _classify(raw)
        target_cls = _TYPE_MAP[target_name]
        uid = raw.get("uid", raw.get("_id"))

        if dry_run:
            log.info("[DRY RUN] uid=%s → %s", uid, target_name)
            stats[target_name] += 1
            continue

        try:
            original_id = raw.get("_id")
            # Build a new typed instance (without _id so Pydantic doesn't complain)
            raw_without_id = {k: v for k, v in raw.items() if k not in ("_id", "_type")}
            contract = target_cls(**raw_without_id)

            # Replace the original document in-place to preserve the _id and
            # avoid creating a duplicate.
            doc_dict = contract.model_dump(mode="python")
            doc_dict["_type"] = target_name
            await collection.replace_one({"_id": original_id}, doc_dict)
            stats[target_name] += 1
            log.info("Migrated uid=%s → %s", uid, target_name)
        except Exception as exc:  # pragma: no cover
            log.error("Failed to migrate uid=%s: %s", uid, exc)
            skipped += 1

    log.info("Migration complete. Stats: %s  Skipped: %d", stats, skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate contracts to typed sub-classes.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect only; do not write to the database.",
    )
    args = parser.parse_args()
    asyncio.run(migrate_contracts(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
