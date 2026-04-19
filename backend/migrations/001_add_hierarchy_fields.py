"""
Migration 001: Add hierarchy fields to existing data.

Contract → Project → Site dependency chain.
Employee type/substitute fields.
Attendance manager-recorded fields.

Run with:
    python -m backend.migrations.run_migration 001

Or directly:
    python backend/migrations/001_add_hierarchy_fields.py
"""

import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def migrate():
    """Apply migration 001 – safe to re-run (idempotent defaults)."""
    # Import here to ensure the database is initialised before use
    from backend.database import init_db
    from backend.models import Employee, Site, Project, Contract, Attendance

    await init_db()
    logger.info("Migration 001: Starting...")

    # ── 1. Employees ──────────────────────────────────────────────────────────
    employees = await Employee.find_all().to_list()
    emp_updated = 0
    for emp in employees:
        changed = False

        # Ensure employee_type is set (old records may not have it)
        if not getattr(emp, 'employee_type', None):
            emp.employee_type = "Company"
            changed = True

        # Substitute fields - set safe defaults for existing records
        if not hasattr(emp, 'can_be_substitute') or emp.can_be_substitute is None:
            emp.can_be_substitute = emp.employee_type == "Outsourced"
            changed = True

        if not hasattr(emp, 'substitute_availability') or emp.substitute_availability is None:
            if emp.employee_type == "Outsourced":
                emp.substitute_availability = "available"
            changed = True

        if not hasattr(emp, 'substitute_assignment_history'):
            emp.substitute_assignment_history = []
            changed = True

        if not hasattr(emp, 'total_substitute_assignments'):
            emp.total_substitute_assignments = 0
            changed = True

        if not hasattr(emp, 'total_days_as_substitute'):
            emp.total_days_as_substitute = 0
            changed = True

        if changed:
            await emp.save()
            emp_updated += 1

    logger.info(f"Migration 001: Updated {emp_updated}/{len(employees)} employees")

    # ── 2. Sites ──────────────────────────────────────────────────────────────
    sites = await Site.find_all().to_list()
    site_updated = 0
    for site in sites:
        changed = False

        if not hasattr(site, 'active_substitute_uids') or site.active_substitute_uids is None:
            site.active_substitute_uids = []
            changed = True

        if not hasattr(site, 'required_workers'):
            site.required_workers = len(getattr(site, 'assigned_employee_ids', []))
            changed = True

        # If project_id is missing, set to 0 as placeholder (must be fixed manually)
        # To identify these sites, query: Site.find(Site.project_id == 0)
        # Then reassign them to the correct project via the workflow UI or API.
        if not getattr(site, 'project_id', None):
            logger.warning(
                f"Site uid={site.uid} ({site.name}) has no project_id – "
                f"set to 0 as placeholder. Reassign via the workflow UI."
            )
            site.project_id = 0
            changed = True

        if changed:
            await site.save()
            site_updated += 1

    logger.info(f"Migration 001: Updated {site_updated}/{len(sites)} sites")

    # ── 3. Projects ────────────────────────────────────────────────────────────
    projects = await Project.find_all().to_list()
    proj_updated = 0
    for project in projects:
        changed = False

        # contract_ids is a list – ensure it's initialised
        if not hasattr(project, 'contract_ids') or project.contract_ids is None:
            project.contract_ids = []
            changed = True

        if changed:
            await project.save()
            proj_updated += 1

    logger.info(f"Migration 001: Updated {proj_updated}/{len(projects)} projects")

    # ── 4. Attendance ──────────────────────────────────────────────────────────
    attendance_records = await Attendance.find_all().to_list()
    att_updated = 0
    for record in attendance_records:
        changed = False

        if not hasattr(record, 'is_substitute') or record.is_substitute is None:
            record.is_substitute = getattr(record, 'is_replacement', False)
            changed = True

        if not hasattr(record, 'recorded_at') or record.recorded_at is None:
            record.recorded_at = datetime.now()
            changed = True

        if changed:
            await record.save()
            att_updated += 1

    logger.info(f"Migration 001: Updated {att_updated}/{len(attendance_records)} attendance records")
    logger.info("Migration 001: COMPLETE ✓")

    return {
        "employees_updated": emp_updated,
        "sites_updated": site_updated,
        "projects_updated": proj_updated,
        "attendance_updated": att_updated,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = asyncio.run(migrate())
    print("Migration result:", result)
