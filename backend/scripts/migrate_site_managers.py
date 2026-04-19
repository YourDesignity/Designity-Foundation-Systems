"""
Migration: Convert single-manager site fields to multi-manager list fields.

Converts:
  - assigned_manager_id  → assigned_manager_ids  = [old_id]
  - assigned_manager_name → assigned_manager_names = [old_name]

Safe to run multiple times (idempotent).
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.database import init_db

logger = logging.getLogger("MigrateSiteManagers")
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


async def migrate_sites() -> None:
    await init_db()

    from backend.models.projects import Site

    sites = await Site.find_all().to_list()
    migrated = 0
    skipped = 0

    for site in sites:
        changed = False

        # Populate assigned_manager_ids from legacy assigned_manager_id if list is empty
        if site.assigned_manager_id and not site.assigned_manager_ids:
            site.assigned_manager_ids = [site.assigned_manager_id]
            changed = True

        # Populate assigned_manager_names from legacy assigned_manager_name if list is empty
        if site.assigned_manager_name and not site.assigned_manager_names:
            site.assigned_manager_names = [site.assigned_manager_name]
            changed = True

        # Ensure legacy primary fields are populated from list if missing
        if not site.assigned_manager_id and site.assigned_manager_ids:
            site.assigned_manager_id = site.assigned_manager_ids[0]
            changed = True
        if not site.assigned_manager_name and site.assigned_manager_names:
            site.assigned_manager_name = site.assigned_manager_names[0]
            changed = True

        if changed:
            await site.save()
            migrated += 1
            logger.info(
                "Migrated site %s (%s): manager_ids=%s",
                site.uid,
                site.name,
                site.assigned_manager_ids,
            )
        else:
            skipped += 1

    logger.info("Migration complete: %d sites migrated, %d sites skipped (already up-to-date).", migrated, skipped)


if __name__ == "__main__":
    asyncio.run(migrate_sites())
