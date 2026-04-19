"""
Phase 5F: Comprehensive Test Data Seed Script
==============================================
Populates the database with realistic test data covering all Phase 5C (Modules),
Phase 5D (Workflow), and Phase 5E (Scheduling) features.

Usage:
    python -m backend.scripts.seed_phase5_data

WARNING: NEVER run against a production database!
"""

from __future__ import annotations

import asyncio
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Bootstrap path so script can be run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from faker import Faker
from passlib.context import CryptContext

from backend.database import DB_NAME, get_next_uid, init_db
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
from backend.models.contracts import LabourContract
from backend.models.base import Counter
from backend.models.schedules import NotificationLog, RecurringSchedule, ScheduledJob
from backend.models.vehicles import TripLog
from backend.models.workflow_history import ApprovalRequest, WorkflowEvent, WorkflowHistory
from backend.config.permissions import get_role_permissions

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_PASSWORD = "Test@123"
NUM_ADMINS = 8          # 1 SuperAdmin, 3 Admins, 4 Site Managers
NUM_PROJECTS = 15
NUM_EMPLOYEES = 60
NUM_VEHICLES = 20
NUM_MATERIALS = 40

# Contract distribution (totals ~35)
NUM_DRAFT = 5
NUM_PENDING_APPROVAL = 5
NUM_ACTIVE = 15
NUM_COMPLETED = 5
NUM_CANCELLED = 5

fake = Faker("en_US")
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================================================================
# STATIC DATA
# =============================================================================

ADMINS_SPEC = [
    {
        "email": "superadmin@phase5.com",
        "full_name": "Super Administrator",
        "designation": "Managing Director",
        "role": "SuperAdmin",
    },
    {
        "email": "alice.morgan@phase5.com",
        "full_name": "Alice Morgan",
        "designation": "Operations Manager",
        "role": "Admin",
    },
    {
        "email": "bob.chen@phase5.com",
        "full_name": "Bob Chen",
        "designation": "Project Director",
        "role": "Admin",
    },
    {
        "email": "carol.hayes@phase5.com",
        "full_name": "Carol Hayes",
        "designation": "Contract Manager",
        "role": "Admin",
    },
    {
        "email": "david.park@phase5.com",
        "full_name": "David Park",
        "designation": "Site Supervisor",
        "role": "Site Manager",
    },
    {
        "email": "emma.lewis@phase5.com",
        "full_name": "Emma Lewis",
        "designation": "Site Supervisor",
        "role": "Site Manager",
    },
    {
        "email": "frank.torres@phase5.com",
        "full_name": "Frank Torres",
        "designation": "Field Manager",
        "role": "Site Manager",
    },
    {
        "email": "grace.kim@phase5.com",
        "full_name": "Grace Kim",
        "designation": "Site Coordinator",
        "role": "Site Manager",
    },
]

PROJECT_NAMES = [
    "Downtown Tower Complex", "Gulf Harbor Renovation", "Northside Residences",
    "Industrial Park Fit-Out", "Lakeside Retail Center", "City Hospital Extension",
    "Westpark School Campus", "Central Parking Structure", "Riverside Sports Club",
    "Grandview Hotel Refurb", "Al-Salam Office Block", "Coastal Warehouse Hub",
    "Tech District Headquarters", "Airport Terminal Upgrade", "Marina Bay Complex",
]

CLIENT_COMPANIES = [
    "Al-Mansour Holdings", "Gulf Construction Corp", "Downtown Developers Inc.",
    "Harbor Realty Partners", "CityBuild International", "Prestige Property Group",
    "Skyline Projects Ltd.", "Meridian Infrastructure", "Orion Building Solutions",
    "Atlas Construction LLC", "Crescent Real Estate", "Falcon Industries",
    "Silver Oak Contractors", "Pioneer Group", "Zenith Developments",
]

DESIGNATIONS = [
    ("Carpenter",    22, 30),
    ("Electrician",  28, 38),
    ("Welder",       25, 35),
    ("Painter",      18, 26),
    ("Labour",       15, 20),
    ("Foreman",      32, 42),
    ("Driver",       18, 25),
    ("Mason",        20, 28),
    ("Plumber",      22, 32),
    ("Supervisor",   35, 45),
]

VEHICLE_SPECS = [
    ("Toyota",        "Hilux",        "Pickup"),
    ("Ford",          "Transit",      "Van"),
    ("Nissan",        "Patrol",       "SUV"),
    ("Mercedes-Benz", "Sprinter",     "Van"),
    ("Toyota",        "Land Cruiser", "SUV"),
    ("Mitsubishi",    "L200",         "Pickup"),
    ("Ford",          "F-150",        "Pickup"),
    ("Isuzu",         "D-Max",        "Pickup"),
    ("Caterpillar",   "320",          "Heavy Equipment"),
    ("Komatsu",       "PC210",        "Heavy Equipment"),
]

MATERIAL_SPECS = [
    ("STL-001", "Structural Steel Beam",  "Steel",           "kg",   15.0, 2.5),
    ("STL-002", "Steel Rebar 12mm",       "Steel",           "kg",   8.0,  1.8),
    ("STL-003", "Steel Plate 6mm",        "Steel",           "m2",   25.0, 6.0),
    ("CON-001", "Ready-Mix Concrete M25", "Concrete",        "m3",   200.0, 65.0),
    ("CON-002", "Concrete Blocks",        "Concrete",        "pcs",  500.0, 1.2),
    ("CON-003", "Cement Bags 50kg",       "Concrete",        "pcs",  300.0, 8.5),
    ("WOD-001", "Plywood 18mm",           "Wood",            "m2",   100.0, 18.0),
    ("WOD-002", "Timber 4x2",             "Wood",            "m",    500.0, 4.5),
    ("WOD-003", "Hardwood Flooring",      "Wood",            "m2",   80.0, 45.0),
    ("TOL-001", "Power Drill",            "Tools",           "pcs",  10.0, 85.0),
    ("TOL-002", "Angle Grinder",          "Tools",           "pcs",  8.0,  65.0),
    ("TOL-003", "Welding Machine",        "Tools",           "pcs",  5.0,  350.0),
    ("TOL-004", "Concrete Mixer",         "Tools",           "pcs",  3.0,  280.0),
    ("SAF-001", "Safety Helmet",          "Safety Equipment","pcs",  50.0, 12.0),
    ("SAF-002", "Safety Vest",            "Safety Equipment","pcs",  80.0, 8.5),
    ("SAF-003", "Safety Harness",         "Safety Equipment","pcs",  20.0, 45.0),
    ("SAF-004", "Work Gloves",            "Safety Equipment","pcs",  100.0,3.5),
    ("SAF-005", "Safety Boots",           "Safety Equipment","pcs",  60.0, 38.0),
    ("ELE-001", "Copper Wire 2.5mm",      "Electrical",      "m",    500.0, 2.8),
    ("ELE-002", "PVC Conduit 20mm",       "Electrical",      "m",    300.0, 1.5),
    ("ELE-003", "Circuit Breaker 20A",    "Electrical",      "pcs",  40.0, 22.0),
    ("ELE-004", "Junction Box",           "Electrical",      "pcs",  60.0, 8.0),
    ("PLM-001", "PVC Pipe 50mm",          "Plumbing",        "m",    200.0, 4.5),
    ("PLM-002", "Copper Pipe 15mm",       "Plumbing",        "m",    150.0, 12.0),
    ("PLM-003", "Ball Valve 25mm",        "Plumbing",        "pcs",  30.0,  18.0),
    ("PLM-004", "Water Pump",             "Plumbing",        "pcs",  5.0,  180.0),
    ("FIN-001", "Ceramic Tiles 60x60",    "Finishing",       "m2",   200.0, 22.0),
    ("FIN-002", "Interior Paint 20L",     "Finishing",       "pcs",  30.0,  65.0),
    ("FIN-003", "Gypsum Board",           "Finishing",       "m2",   150.0, 12.0),
    ("FIN-004", "Aluminum Window",        "Finishing",       "m2",   80.0, 95.0),
    ("INS-001", "Glass Wool Insulation",  "Insulation",      "m2",   300.0, 8.0),
    ("INS-002", "Foam Board 50mm",        "Insulation",      "m2",   200.0, 15.0),
    ("CHM-001", "Waterproofing Compound", "Chemicals",       "kg",   100.0, 18.0),
    ("CHM-002", "Tile Adhesive",          "Chemicals",       "kg",   200.0, 6.5),
    ("CHM-003", "Grout 5kg",              "Chemicals",       "pcs",  80.0,  12.0),
    ("ACC-001", "Door Hinges Set",        "Accessories",     "set",  50.0,  15.0),
    ("ACC-002", "Door Lock Set",          "Accessories",     "set",  40.0,  35.0),
    ("ACC-003", "Window Handle",          "Accessories",     "set",  60.0,  12.0),
    ("MSC-001", "Scaffolding Pipe",       "Scaffolding",     "m",    200.0, 5.5),
    ("MSC-002", "Scaffolding Clamp",      "Scaffolding",     "pcs",  500.0, 2.0),
]

# =============================================================================
# UTILITIES
# =============================================================================


def hashed(plain: str) -> str:
    return pwd_ctx.hash(plain)


def now() -> datetime:
    return datetime.now()


def days_ago(n: int) -> datetime:
    return now() - timedelta(days=n)


def days_from_now(n: int) -> datetime:
    return now() + timedelta(days=n)


def to_midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


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
# SECTION 1: ADMINS
# =============================================================================


async def create_admins() -> List[Admin]:
    """Create 1 SuperAdmin, 3 Admins, 4 Site Managers."""
    print("\n📋 Creating admins...")
    admins = []
    pw = hashed(DEFAULT_PASSWORD)
    for spec in ADMINS_SPEC:
        uid = await get_next_uid("admins")
        role_perms = get_role_permissions(spec["role"])
        admin = Admin(
            uid=uid,
            email=spec["email"],
            hashed_password=pw,
            full_name=spec["full_name"],
            designation=spec["designation"],
            role=spec["role"],
            permissions=role_perms,
            phone=fake.numerify("+965-####-####"),
        )
        await admin.insert()
        admins.append(admin)
    print(f"   ✅ Created {len(admins)} admins")
    return admins


# =============================================================================
# SECTION 2: PROJECTS & CONTRACTS
# =============================================================================


async def create_projects_and_contracts(
    admins: List[Admin],
) -> Tuple[List[Project], List[LabourContract]]:
    """
    Create 15 projects and ~35 contracts with various workflow states and dates.
    """
    print("\n📋 Creating projects and contracts...")

    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])
    managers = [a for a in admins if a.role == "Site Manager"]

    projects: List[Project] = []
    contracts: List[LabourContract] = []

    # Date helpers for specific contract distributions
    def future_start(days_offset: int) -> Tuple[datetime, datetime]:
        """Future start: starts in X days, runs 120-365 days."""
        start = to_midnight(days_from_now(days_offset))
        end = to_midnight(start + timedelta(days=random.randint(120, 365)))
        return start, end

    def currently_active() -> Tuple[datetime, datetime]:
        """Currently running: started 30-180 days ago, ends 30-365 days from now."""
        started = to_midnight(days_ago(random.randint(30, 180)))
        end = to_midnight(days_from_now(random.randint(30, 365)))
        return started, end

    def expiring_soon(days_remaining: int) -> Tuple[datetime, datetime]:
        """Expiring in exactly X days from now."""
        end = to_midnight(days_from_now(days_remaining))
        start = to_midnight(end - timedelta(days=random.randint(60, 300)))
        return start, end

    def completed_contract() -> Tuple[datetime, datetime]:
        """Already ended: ended 1-90 days ago."""
        end = to_midnight(days_ago(random.randint(1, 90)))
        start = to_midnight(end - timedelta(days=random.randint(60, 300)))
        return start, end

    def cancelled_contract() -> Tuple[datetime, datetime]:
        """Cancelled: started some time ago, ended before today."""
        start = to_midnight(days_ago(random.randint(90, 365)))
        end = to_midnight(start + timedelta(days=random.randint(30, 180)))
        return start, end

    # Build contract date/state schedule
    # 5 DRAFT (future starts)
    # 5 PENDING_APPROVAL (future starts + recent active)
    # 15 ACTIVE (10 currently active + 5 expiring soon)
    # 5 COMPLETED (already ended)
    # 5 CANCELLED (various)

    contract_schedule: List[Dict[str, Any]] = []

    # DRAFT contracts with future start dates
    for i, days_offset in enumerate([10, 15, 20, 25, 30]):
        s, e = future_start(days_offset)
        contract_schedule.append(
            {"workflow_state": "DRAFT", "status": "On Hold", "start": s, "end": e}
        )

    # PENDING_APPROVAL contracts
    for i, days_offset in enumerate([10, 18, 22, 28, 12]):
        s, e = future_start(days_offset)
        contract_schedule.append(
            {"workflow_state": "PENDING_APPROVAL", "status": "On Hold", "start": s, "end": e}
        )

    # ACTIVE contracts (10 running + 5 expiring soon)
    for _ in range(10):
        s, e = currently_active()
        contract_schedule.append(
            {"workflow_state": "ACTIVE", "status": "Active", "start": s, "end": e}
        )
    for days_remaining in [7, 15, 25, 32, 45]:
        s, e = expiring_soon(days_remaining)
        contract_schedule.append(
            {"workflow_state": "ACTIVE", "status": "Active", "start": s, "end": e}
        )

    # COMPLETED contracts
    for _ in range(5):
        s, e = completed_contract()
        contract_schedule.append(
            {"workflow_state": "COMPLETED", "status": "Completed", "start": s, "end": e}
        )

    # CANCELLED contracts
    for _ in range(5):
        s, e = cancelled_contract()
        contract_schedule.append(
            {"workflow_state": "CANCELLED", "status": "Cancelled", "start": s, "end": e}
        )

    # Module config pools
    module_options = [
        (["employee"], {"employee": {"max_employees": 10, "cost_per_employee_day": 15.0, "overtime_rate": 1.5}}),
        (["employee"], {"employee": {"max_employees": 8, "cost_per_employee_day": 12.0, "overtime_rate": 1.5}}),
        (["inventory"], {"inventory": {"track_materials": True, "auto_reorder": False, "cost_calculation_method": "FIFO"}}),
        (["inventory"], {"inventory": {"track_materials": True, "auto_reorder": True, "cost_calculation_method": "LIFO"}}),
        (["vehicle"], {"vehicle": {"max_vehicles": 5, "fuel_cost_per_km": 0.5, "maintenance_alerts": True}}),
        (["employee", "inventory"], {
            "employee": {"max_employees": 12, "cost_per_employee_day": 14.0, "overtime_rate": 1.5},
            "inventory": {"track_materials": True, "auto_reorder": False, "cost_calculation_method": "FIFO"},
        }),
        (["employee", "vehicle"], {
            "employee": {"max_employees": 8, "cost_per_employee_day": 15.0, "overtime_rate": 1.5},
            "vehicle": {"max_vehicles": 3, "fuel_cost_per_km": 0.45, "maintenance_alerts": True},
        }),
        (["employee", "inventory", "vehicle"], {
            "employee": {"max_employees": 15, "cost_per_employee_day": 16.0, "overtime_rate": 1.5},
            "inventory": {"track_materials": True, "auto_reorder": True, "cost_calculation_method": "FIFO"},
            "vehicle": {"max_vehicles": 5, "fuel_cost_per_km": 0.5, "maintenance_alerts": True},
        }),
    ]

    # Create 15 projects, distributing ~2-3 contracts each
    contracts_per_project = [2, 2, 3, 2, 3, 2, 2, 3, 2, 2, 2, 2, 3, 2, 3]  # sums to 35
    contract_idx = 0

    for p_idx in range(NUM_PROJECTS):
        proj_uid = await get_next_uid("projects")
        proj_name = PROJECT_NAMES[p_idx % len(PROJECT_NAMES)]
        client = CLIENT_COMPANIES[p_idx % len(CLIENT_COMPANIES)]

        project = Project(
            uid=proj_uid,
            project_code=f"PRJ-{proj_uid:03d}",
            project_name=proj_name,
            client_name=client,
            client_contact=fake.name(),
            client_email=fake.company_email(),
            description=f"{proj_name} for {client}. Full construction and fit-out.",
            status="Active",
            created_by_admin_id=super_admin.uid,
        )
        await project.insert()
        projects.append(project)

        # Create contracts for this project
        n_contracts = contracts_per_project[p_idx]
        for _ in range(n_contracts):
            if contract_idx >= len(contract_schedule):
                break

            sched = contract_schedule[contract_idx]
            contract_idx += 1

            cnt_uid = await get_next_uid("contracts")
            contract_code = f"CNT-{cnt_uid:03d}"
            wf_state = sched["workflow_state"]
            cnt_status = sched["status"]
            start_dt = sched["start"]
            end_dt = sched["end"]

            # Assign modules for ACTIVE/COMPLETED contracts
            enabled_modules: List[str] = []
            module_config: Dict[str, Any] = {}
            workflow_metadata: Dict[str, Any] = {}
            manager = random.choice(managers) if managers else None

            if wf_state in ("ACTIVE", "COMPLETED"):
                mod_choice = random.choice(module_options)
                enabled_modules, module_config = mod_choice

                # Sample cost metadata for ACTIVE contracts
                workflow_metadata = {
                    "cost_2026_03": {
                        "month": 3,
                        "year": 2026,
                        "total_cost": round(random.uniform(5000, 25000), 2),
                        "by_module": {
                            m: {
                                "total_cost": round(random.uniform(1000, 10000), 2),
                                "item_count": random.randint(3, 15),
                            }
                            for m in enabled_modules
                        },
                        "calculated_at": "2026-04-01T01:00:00",
                    }
                }

            # Set state_changed_at based on state
            state_changed_at = None
            if wf_state == "ACTIVE":
                state_changed_at = days_ago(random.randint(5, 60))
            elif wf_state == "COMPLETED":
                state_changed_at = end_dt + timedelta(days=1)
            elif wf_state == "CANCELLED":
                state_changed_at = days_ago(random.randint(5, 90))
            elif wf_state == "PENDING_APPROVAL":
                state_changed_at = days_ago(random.randint(1, 10))

            contract = LabourContract(
                uid=cnt_uid,
                contract_code=contract_code,
                contract_name=f"{proj_name} – Contract {cnt_uid}",
                contract_type="Labour",
                project_id=proj_uid,
                project_name=proj_name,
                client_name=client,
                start_date=start_dt,
                end_date=end_dt,
                contract_value=round(random.uniform(20000, 200000), 2),
                payment_terms=random.choice(["Monthly", "Milestone-based", "Quarterly"]),
                status=cnt_status,
                enabled_modules=list(enabled_modules),
                module_config=module_config,
                workflow_state=wf_state,
                workflow_metadata=workflow_metadata,
                state_changed_at=state_changed_at,
                state_changed_by=manager.uid if manager else None,
                created_by_admin_id=super_admin.uid,
            )
            await contract.insert()
            contracts.append(contract)

        # Update project with contract IDs
        project.contract_ids = [
            c.uid for c in contracts if c.project_id == proj_uid
        ]
        await project.save()

    print(f"   ✅ Created {len(projects)} projects and {len(contracts)} contracts")
    by_state: Dict[str, int] = {}
    for c in contracts:
        by_state[c.workflow_state] = by_state.get(c.workflow_state, 0) + 1
    for state, count in sorted(by_state.items()):
        print(f"      - {state}: {count}")
    return projects, contracts


# =============================================================================
# SECTION 3: EMPLOYEES
# =============================================================================


async def create_employees(admins: List[Admin]) -> List[Employee]:
    """Create 60 employees with various designations and statuses."""
    print("\n📋 Creating employees...")
    employees = []
    manager = next((a for a in admins if a.role == "Site Manager"), admins[0])

    for i in range(NUM_EMPLOYEES):
        uid = await get_next_uid("employees")
        desig, sal_min, sal_max = DESIGNATIONS[i % len(DESIGNATIONS)]
        status = "Inactive" if i >= 50 else "Active"
        salary = round(random.uniform(sal_min * 10, sal_max * 10), 2)
        allowance = round(salary * random.uniform(0.1, 0.2), 2)

        emp = Employee(
            uid=uid,
            name=fake.name(),
            designation=desig,
            status=status,
            employee_type="Company",
            nationality=random.choice(["Indian", "Pakistani", "Egyptian", "Filipino", "Kuwaiti"]),
            phone_kuwait=fake.numerify("+965-####-####"),
            basic_salary=salary,
            allowance=allowance,
            standard_work_days=28,
            date_of_joining=days_ago(random.randint(30, 1825)),
        )
        await emp.insert()
        employees.append(emp)

    active_count = sum(1 for e in employees if e.status == "Active")
    print(f"   ✅ Created {len(employees)} employees ({active_count} active, {len(employees) - active_count} inactive)")
    return employees


# =============================================================================
# SECTION 4: VEHICLES
# =============================================================================


async def create_vehicles() -> List[Vehicle]:
    """Create 20 vehicles with various types and statuses."""
    print("\n📋 Creating vehicles...")
    vehicles = []
    statuses = ["Available"] * 12 + ["In Use"] * 5 + ["Under Maintenance"] * 3

    used_plates: set = set()
    for i in range(NUM_VEHICLES):
        uid = await get_next_uid("vehicles")
        make, model, vtype = VEHICLE_SPECS[i % len(VEHICLE_SPECS)]
        year = random.randint(2018, 2024)
        # Ensure unique plate
        while True:
            plate = f"KWT {fake.numerify('####')} {random.choice('ABCDEFGH')}"
            if plate not in used_plates:
                used_plates.add(plate)
                break

        vehicle = Vehicle(
            uid=uid,
            model=f"{year} {make} {model}",
            plate=plate,
            type=vtype,
            status=statuses[i],
            current_mileage=random.uniform(5000, 150000),
            registration_expiry=(now() + timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
            insurance_expiry=(now() + timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
        )
        await vehicle.insert()
        vehicles.append(vehicle)

    print(f"   ✅ Created {len(vehicles)} vehicles")
    return vehicles


# =============================================================================
# SECTION 5: MATERIALS
# =============================================================================


async def create_materials() -> List[Material]:
    """Create 40 materials across various categories."""
    print("\n📋 Creating materials...")
    materials = []
    for code, name, category, uom, qty, unit_cost in MATERIAL_SPECS:
        uid = await get_next_uid("materials")
        mat = Material(
            uid=uid,
            material_code=code,
            name=name,
            category=category.lower().replace(" ", "_"),
            unit_of_measure=uom,
            current_stock=qty,
            minimum_stock=round(qty * 0.15, 1),
            unit_cost=unit_cost,
            description=f"{name} – standard grade",
        )
        await mat.insert()
        materials.append(mat)
    print(f"   ✅ Created {len(materials)} materials")
    return materials


# =============================================================================
# SECTION 6: MODULE ASSIGNMENTS
# =============================================================================


async def create_module_assignments(
    contracts: List[LabourContract],
    employees: List[Employee],
    vehicles: List[Vehicle],
    materials: List[Material],
    admins: List[Admin],
) -> Tuple[int, int, int]:
    """
    Link modules to ACTIVE/COMPLETED contracts via existing assignment models.
    Returns (emp_assignments, material_movements, vehicle_trips) counts.
    """
    print("\n📋 Creating module assignments...")
    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])
    active_employees = [e for e in employees if e.status == "Active"]

    total_emp_assignments = 0
    total_material_movements = 0
    total_vehicle_trips = 0

    active_contracts = [c for c in contracts if c.workflow_state in ("ACTIVE", "COMPLETED")]
    site_uid_counter = [0]  # mutable closure for site UIDs

    for contract in active_contracts:
        modules = contract.enabled_modules

        # ── Employee module ────────────────────────────────────────────────
        if "employee" in modules and active_employees:
            max_emp = contract.module_config.get("employee", {}).get("max_employees", 8)
            n_assign = random.randint(3, min(max_emp, len(active_employees)))
            assigned_emps = random.sample(active_employees, n_assign)

            # Create a minimal contract site
            site_uid = await get_next_uid("sites")
            site = Site(
                uid=site_uid,
                name=f"Site for {contract.contract_code}",
                location=fake.address().replace("\n", ", "),
                project_id=contract.project_id,
                project_name=contract.project_name,
                contract_id=contract.uid,
                contract_code=contract.contract_code,
                status="Active" if contract.workflow_state == "ACTIVE" else "Completed",
                required_workers=n_assign,
                assigned_workers=n_assign,
                assigned_employee_ids=[e.uid for e in assigned_emps],
                start_date=contract.start_date,
            )
            await site.insert()

            for emp in assigned_emps:
                ea_uid = await get_next_uid("employee_assignments")
                ea = EmployeeAssignment(
                    uid=ea_uid,
                    employee_id=emp.uid,
                    employee_name=emp.name,
                    employee_type=emp.employee_type,
                    employee_designation=emp.designation,
                    assignment_type="Permanent",
                    project_id=contract.project_id,
                    project_name=contract.project_name,
                    contract_id=contract.uid,
                    site_id=site_uid,
                    site_name=site.name,
                    assigned_date=days_ago(random.randint(5, 60)),
                    assignment_start=contract.start_date,
                    assignment_end=None if contract.workflow_state == "ACTIVE" else contract.end_date,
                    status="Active" if contract.workflow_state == "ACTIVE" else "Completed",
                    created_by_admin_id=super_admin.uid,
                )
                await ea.insert()
                total_emp_assignments += 1

        # ── Inventory module ───────────────────────────────────────────────
        if "inventory" in modules and materials:
            n_materials = random.randint(5, min(15, len(materials)))
            selected_mats = random.sample(materials, n_materials)
            for mat in selected_mats:
                mm_uid = await get_next_uid("material_movements")
                qty_used = round(random.uniform(5.0, 50.0), 2)
                total_cost = round(qty_used * mat.unit_cost, 2)
                movement = MaterialMovement(
                    uid=mm_uid,
                    material_id=mat.uid,
                    material_name=mat.name,
                    movement_type="OUT",
                    quantity=qty_used,
                    unit_cost=mat.unit_cost,
                    total_cost=total_cost,
                    reference_type="contract_usage",
                    reference_id=contract.uid,
                    reference_code=contract.contract_code,
                    notes=f"Used on {contract.contract_code}",
                    performed_by_admin_id=super_admin.uid,
                )
                await movement.insert()
                total_material_movements += 1

        # ── Vehicle module ─────────────────────────────────────────────────
        if "vehicle" in modules and vehicles:
            max_veh = contract.module_config.get("vehicle", {}).get("max_vehicles", 3)
            n_vehicles = random.randint(1, min(max_veh, len(vehicles)))
            selected_vehs = random.sample(vehicles, n_vehicles)
            for veh in selected_vehs:
                trip_uid = await get_next_uid("vehicle_trips")
                start_mileage = round(veh.current_mileage + random.uniform(0, 500), 1)
                trip = TripLog(
                    uid=trip_uid,
                    vehicle_uid=veh.uid,
                    vehicle_plate=veh.plate,
                    driver_name=fake.name(),
                    purpose=f"Contract work – {contract.contract_code}",
                    status="Completed",
                    start_mileage=start_mileage,
                    end_mileage=round(start_mileage + random.uniform(20, 200), 1),
                    out_time=days_ago(random.randint(1, 30)),
                    in_time=days_ago(random.randint(0, 1)),
                    specs={"contract_uid": contract.uid, "contract_code": contract.contract_code},
                )
                await trip.insert()
                total_vehicle_trips += 1

    print(f"   ✅ Employee assignments:  {total_emp_assignments}")
    print(f"   ✅ Material movements:    {total_material_movements}")
    print(f"   ✅ Vehicle trips:         {total_vehicle_trips}")
    return total_emp_assignments, total_material_movements, total_vehicle_trips


# =============================================================================
# SECTION 7: WORKFLOW HISTORY
# =============================================================================


async def create_workflow_history(
    contracts: List[LabourContract],
    admins: List[Admin],
) -> int:
    """Create WorkflowHistory records for all state transitions."""
    print("\n📋 Creating workflow history...")
    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])
    managers = [a for a in admins if a.role == "Site Manager"]
    manager = managers[0] if managers else super_admin

    total = 0

    for contract in contracts:
        state = contract.workflow_state
        cid = contract.uid

        async def add_history(from_s: str, to_s: str, reason: str, ts: datetime, actor_id: int) -> None:
            nonlocal total
            h = WorkflowHistory(
                contract_id=cid,
                from_state=from_s,
                to_state=to_s,
                changed_by=actor_id,
                reason=reason,
                timestamp=ts,
            )
            await h.insert()
            total += 1

        # Every contract starts as DRAFT
        await add_history("", "DRAFT", "Contract created", days_ago(70), super_admin.uid)

        if state == "DRAFT":
            # Just the creation event
            pass

        elif state == "PENDING_APPROVAL":
            await add_history("DRAFT", "PENDING_APPROVAL", "Submitted for approval",
                              days_ago(5), super_admin.uid)

        elif state == "ACTIVE":
            await add_history("DRAFT", "PENDING_APPROVAL", "Submitted for approval",
                              days_ago(60), super_admin.uid)
            await add_history("PENDING_APPROVAL", "ACTIVE", "All approvals received",
                              days_ago(55), manager.uid)

        elif state == "COMPLETED":
            await add_history("DRAFT", "PENDING_APPROVAL", "Submitted for approval",
                              days_ago(90), super_admin.uid)
            await add_history("PENDING_APPROVAL", "ACTIVE", "All approvals received",
                              days_ago(85), manager.uid)
            await add_history("ACTIVE", "COMPLETED", "Contract period ended",
                              days_ago(2), super_admin.uid)

        elif state == "CANCELLED":
            choice = random.random()
            if choice < 0.5:
                # DRAFT → CANCELLED
                await add_history("DRAFT", "CANCELLED", "Budget constraints",
                                  days_ago(30), super_admin.uid)
            else:
                # DRAFT → PENDING → CANCELLED
                await add_history("DRAFT", "PENDING_APPROVAL", "Submitted for approval",
                                  days_ago(50), super_admin.uid)
                await add_history("PENDING_APPROVAL", "CANCELLED", "Approval rejected",
                                  days_ago(45), manager.uid)

    print(f"   ✅ Created {total} workflow history records")
    return total


# =============================================================================
# SECTION 8: APPROVAL REQUESTS
# =============================================================================


async def create_approval_requests(
    contracts: List[LabourContract],
    admins: List[Admin],
) -> int:
    """Create ApprovalRequest documents for relevant contracts."""
    print("\n📋 Creating approval requests...")
    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])
    managers = [a for a in admins if a.role == "Site Manager"]
    total = 0

    pending_contracts = [c for c in contracts if c.workflow_state == "PENDING_APPROVAL"]
    active_contracts = [c for c in contracts if c.workflow_state == "ACTIVE"]
    cancelled_contracts = [c for c in contracts if c.workflow_state == "CANCELLED"]

    # PENDING approval requests
    for contract in pending_contracts:
        required = [m.uid for m in managers[:2]] if len(managers) >= 2 else [managers[0].uid]
        ar = ApprovalRequest(
            contract_id=contract.uid,
            approval_type="contract_activation",
            status="PENDING",
            required_approvers=required,
            pending_approvers=required,
            approved_by=[],
            requested_by=super_admin.uid,
            created_at=days_ago(5),
            updated_at=days_ago(5),
        )
        await ar.insert()
        total += 1

    # APPROVED requests for ACTIVE contracts (not all of them)
    for contract in active_contracts[:10]:
        approver = managers[0] if managers else super_admin
        ar = ApprovalRequest(
            contract_id=contract.uid,
            approval_type="contract_activation",
            status="APPROVED",
            required_approvers=[approver.uid],
            pending_approvers=[],
            approved_by=[approver.uid],
            requested_by=super_admin.uid,
            created_at=days_ago(58),
            updated_at=days_ago(55),
        )
        await ar.insert()
        total += 1

    # REJECTED requests for some CANCELLED contracts
    for contract in cancelled_contracts[:3]:
        approver = managers[0] if managers else super_admin
        ar = ApprovalRequest(
            contract_id=contract.uid,
            approval_type="contract_activation",
            status="REJECTED",
            required_approvers=[approver.uid],
            pending_approvers=[],
            approved_by=[],
            rejected_by=approver.uid,
            rejection_reason="Budget exceeds approved limit",
            requested_by=super_admin.uid,
            created_at=days_ago(30),
            updated_at=days_ago(28),
        )
        await ar.insert()
        total += 1

    print(f"   ✅ Created {total} approval requests")
    return total


# =============================================================================
# SECTION 9: SCHEDULED JOBS
# =============================================================================


async def create_scheduled_jobs(contracts: List[LabourContract]) -> int:
    """Create ScheduledJob records for various automation scenarios."""
    print("\n📋 Creating scheduled jobs...")
    total = 0

    draft_contracts = [c for c in contracts if c.workflow_state == "DRAFT"]
    active_contracts = [c for c in contracts if c.workflow_state == "ACTIVE"]
    active_expiring = sorted(
        [c for c in active_contracts if c.end_date > now()],
        key=lambda c: c.end_date,
    )[:5]
    cancelled_contracts = [c for c in contracts if c.workflow_state == "CANCELLED"]

    async def add_job(**kwargs: Any) -> None:
        nonlocal total
        uid = await get_next_uid("scheduled_jobs")
        job = ScheduledJob(uid=uid, **kwargs)
        await job.insert()
        total += 1

    # Future-start contracts → contract_activation job
    for contract in draft_contracts:
        await add_job(
            job_type="contract_activation",
            target_type="contract",
            target_id=contract.uid,
            scheduled_for=contract.start_date,
            status="PENDING",
            payload={"contract_id": contract.uid, "contract_code": contract.contract_code},
        )

    # Expiring-soon ACTIVE contracts → expiry warning + auto_completion jobs
    for contract in active_expiring:
        end = contract.end_date
        for days_before, job_type in [(30, "contract_expiry_warning_30"),
                                      (15, "contract_expiry_warning_15"),
                                      (7, "contract_expiry_warning_7")]:
            scheduled_for = end - timedelta(days=days_before)
            job_status = "COMPLETED" if scheduled_for < now() else "PENDING"
            completed_at = now() - timedelta(hours=1) if job_status == "COMPLETED" else None
            await add_job(
                job_type=job_type,
                target_type="contract",
                target_id=contract.uid,
                scheduled_for=scheduled_for,
                status=job_status,
                completed_at=completed_at,
                payload={"contract_id": contract.uid, "days_remaining": days_before},
            )

        # Auto-completion on end_date
        auto_status = "COMPLETED" if end < now() else "PENDING"
        await add_job(
            job_type="contract_auto_completion",
            target_type="contract",
            target_id=contract.uid,
            scheduled_for=end,
            status=auto_status,
            payload={"contract_id": contract.uid},
        )

        # Renewal request 60 days before end
        renewal_date = end - timedelta(days=60)
        renewal_status = "COMPLETED" if renewal_date < now() else "PENDING"
        await add_job(
            job_type="renewal_request",
            target_type="contract",
            target_id=contract.uid,
            scheduled_for=renewal_date,
            status=renewal_status,
            completed_at=days_ago(5) if renewal_status == "COMPLETED" else None,
            payload={"contract_id": contract.uid},
        )

    # Monthly cost calculation jobs for ACTIVE contracts (next cycle)
    for contract in active_contracts[:8]:
        await add_job(
            job_type="monthly_cost_calculation",
            target_type="contract",
            target_id=contract.uid,
            scheduled_for=datetime(2026, 5, 1, 1, 0, 0),
            status="PENDING",
            payload={"month": 5, "year": 2026, "contract_id": contract.uid},
        )

    # FAILED jobs for cancelled contracts (testing retry logic)
    for contract in cancelled_contracts[:3]:
        await add_job(
            job_type="contract_activation",
            target_type="contract",
            target_id=contract.uid,
            scheduled_for=days_ago(10),
            status="FAILED",
            retry_count=3,
            max_retries=3,
            last_error="Contract not in valid state for activation",
            payload={"contract_id": contract.uid},
        )

    print(f"   ✅ Created {total} scheduled jobs")
    return total


# =============================================================================
# SECTION 10: NOTIFICATION LOGS
# =============================================================================


async def create_notification_logs(
    contracts: List[LabourContract],
    admins: List[Admin],
) -> int:
    """Create NotificationLog records for various notification types."""
    print("\n📋 Creating notification logs...")
    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])
    total = 0

    active_contracts = [c for c in contracts if c.workflow_state == "ACTIVE"]
    completed_contracts = [c for c in contracts if c.workflow_state == "COMPLETED"]

    async def add_notification(**kwargs: Any) -> None:
        nonlocal total
        nl = NotificationLog(**kwargs)
        await nl.insert()
        total += 1

    # Expiry warnings for ACTIVE contracts ending within 45 days
    expiring = [c for c in active_contracts if 0 < (c.end_date - now()).days <= 45]
    for contract in expiring:
        days_left = (contract.end_date - now()).days
        recipient = super_admin.uid
        for channel in ("email", "in_app"):
            urgent = days_left <= 7
            subject = (
                f"{'URGENT: ' if urgent else ''}Contract {contract.contract_code} "
                f"expires in {days_left} days"
            )
            await add_notification(
                notification_type="expiry_warning",
                recipient_type="admin",
                recipient_id=recipient,
                channel=channel,
                subject=subject,
                body=(
                    f"This is an automated reminder that contract {contract.contract_code} "
                    f"is expiring in {days_left} day(s). Please review and take action."
                ),
                sent_at=days_ago(1),
                status="SENT",
                metadata={"contract_id": contract.uid, "days_remaining": days_left},
            )

    # Renewal reminders
    for contract in active_contracts[:5]:
        await add_notification(
            notification_type="renewal_reminder",
            recipient_type="admin",
            recipient_id=super_admin.uid,
            channel="email",
            subject=f"Renewal Required: Contract {contract.contract_code}",
            body=(
                f"Contract {contract.contract_code} is approaching expiry. "
                "A renewal approval request has been created."
            ),
            sent_at=days_ago(10),
            status="SENT",
            metadata={"contract_id": contract.uid},
        )

    # Payment reminders for ACTIVE contracts
    for contract in active_contracts[:6]:
        await add_notification(
            notification_type="payment_reminder",
            recipient_type="admin",
            recipient_id=super_admin.uid,
            channel="email",
            subject=f"Payment Reminder: Contract {contract.contract_code}",
            body=f"This is your monthly payment reminder for {contract.contract_code}.",
            sent_at=days_ago(15),
            status="SENT",
            metadata={"contract_id": contract.uid},
        )

    # Completion notifications for COMPLETED contracts
    for contract in completed_contracts:
        await add_notification(
            notification_type="contract_completed",
            recipient_type="admin",
            recipient_id=super_admin.uid,
            channel="email",
            subject=f"Contract {contract.contract_code} Completed",
            body=(
                f"Contract {contract.contract_code} has been automatically completed "
                "on its end date."
            ),
            sent_at=days_ago(random.randint(1, 30)),
            status="SENT",
            metadata={"contract_id": contract.uid},
        )

    # FAILED notifications (testing error handling)
    for _ in range(5):
        await add_notification(
            notification_type="expiry_warning",
            recipient_type="admin",
            recipient_id=9999,  # Non-existent admin
            channel="sms",
            subject="Contract expiry warning",
            body="This is an automated expiry warning.",
            sent_at=None,
            status="FAILED",
            error="Recipient not found",
            metadata={},
        )

    print(f"   ✅ Created {total} notification logs")
    return total


# =============================================================================
# SECTION 11: RECURRING SCHEDULES
# =============================================================================


async def create_recurring_schedules() -> int:
    """Seed the 3 built-in recurring schedules."""
    print("\n📋 Creating recurring schedules...")
    schedules_spec = [
        {
            "name": "monthly_cost_calculation",
            "description": "Calculate costs for all active contracts on the 1st of every month.",
            "schedule_type": "monthly",
            "cron_expression": "0 1 1 * *",
            "job_type": "monthly_cost_calculation",
            "enabled": True,
            "next_run": datetime(2026, 5, 1, 1, 0, 0),
        },
        {
            "name": "payment_reminders",
            "description": "Send payment reminders on the 5th of every month.",
            "schedule_type": "monthly",
            "cron_expression": "0 9 5 * *",
            "job_type": "payment_reminder",
            "enabled": True,
            "next_run": datetime(2026, 5, 5, 9, 0, 0),
        },
        {
            "name": "monthly_report_generation",
            "description": "Generate progress reports on the 28th of every month.",
            "schedule_type": "monthly",
            "cron_expression": "0 23 28 * *",
            "job_type": "report_generation",
            "enabled": True,
            "next_run": datetime(2026, 4, 28, 23, 0, 0),
        },
    ]

    for spec in schedules_spec:
        rs = RecurringSchedule(**spec)
        await rs.insert()

    print(f"   ✅ Created {len(schedules_spec)} recurring schedules")
    return len(schedules_spec)


# =============================================================================
# SECTION 12: WORKFLOW EVENTS
# =============================================================================


async def create_workflow_events(contracts: List[LabourContract]) -> int:
    """Create WorkflowEvent audit entries for key contract actions."""
    print("\n📋 Creating workflow events...")
    total = 0

    active_contracts = [c for c in contracts if c.workflow_state == "ACTIVE"]
    completed_contracts = [c for c in contracts if c.workflow_state == "COMPLETED"]

    for contract in active_contracts[:10]:
        event = WorkflowEvent(
            event_type="STATE_CHANGED",
            payload={
                "contract_id": contract.uid,
                "contract_code": contract.contract_code,
                "from_state": "PENDING_APPROVAL",
                "to_state": "ACTIVE",
            },
            timestamp=days_ago(random.randint(5, 60)),
        )
        await event.insert()
        total += 1

    for contract in completed_contracts:
        event = WorkflowEvent(
            event_type="STATE_CHANGED",
            payload={
                "contract_id": contract.uid,
                "contract_code": contract.contract_code,
                "from_state": "ACTIVE",
                "to_state": "COMPLETED",
            },
            timestamp=days_ago(random.randint(1, 30)),
        )
        await event.insert()
        total += 1

    print(f"   ✅ Created {total} workflow events")
    return total


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


async def main() -> None:
    start_time = time.time()
    print("=" * 60)
    print("  Phase 5F: Comprehensive Test Data Seed Script")
    print("=" * 60)

    if not safety_check():
        sys.exit(1)

    print(f"\n🔌 Connecting to database: {DB_NAME}")
    try:
        await init_db()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

    # Prompt for confirmation
    print(f"\n⚠️  This will insert Phase 5 test data into: {DB_NAME}")
    answer = input("   Continue? [y/N]: ").strip().lower()
    if answer != "y":
        print("   Aborted.")
        sys.exit(0)

    errors: List[str] = []

    # 1. Admins
    try:
        admins = await create_admins()
    except Exception as e:
        print(f"❌ Admins failed: {e}")
        errors.append(f"Admins: {e}")
        admins = []

    # 2. Projects & Contracts
    try:
        projects, contracts = await create_projects_and_contracts(admins)
    except Exception as e:
        print(f"❌ Projects/Contracts failed: {e}")
        errors.append(f"Projects/Contracts: {e}")
        projects, contracts = [], []

    # 3. Employees
    try:
        employees = await create_employees(admins)
    except Exception as e:
        print(f"❌ Employees failed: {e}")
        errors.append(f"Employees: {e}")
        employees = []

    # 4. Vehicles
    try:
        vehicles = await create_vehicles()
    except Exception as e:
        print(f"❌ Vehicles failed: {e}")
        errors.append(f"Vehicles: {e}")
        vehicles = []

    # 5. Materials
    try:
        materials = await create_materials()
    except Exception as e:
        print(f"❌ Materials failed: {e}")
        errors.append(f"Materials: {e}")
        materials = []

    # 6. Module assignments
    try:
        if contracts and employees:
            await create_module_assignments(contracts, employees, vehicles, materials, admins)
        else:
            print("   ⚠️  Skipped module assignments (no contracts or employees)")
    except Exception as e:
        print(f"❌ Module assignments failed: {e}")
        errors.append(f"Module assignments: {e}")

    # 7. Workflow history
    try:
        if contracts:
            await create_workflow_history(contracts, admins)
        else:
            print("   ⚠️  Skipped workflow history (no contracts)")
    except Exception as e:
        print(f"❌ Workflow history failed: {e}")
        errors.append(f"Workflow history: {e}")

    # 8. Approval requests
    try:
        if contracts:
            await create_approval_requests(contracts, admins)
        else:
            print("   ⚠️  Skipped approval requests (no contracts)")
    except Exception as e:
        print(f"❌ Approval requests failed: {e}")
        errors.append(f"Approval requests: {e}")

    # 9. Scheduled jobs
    try:
        if contracts:
            await create_scheduled_jobs(contracts)
        else:
            print("   ⚠️  Skipped scheduled jobs (no contracts)")
    except Exception as e:
        print(f"❌ Scheduled jobs failed: {e}")
        errors.append(f"Scheduled jobs: {e}")

    # 10. Notification logs
    try:
        if contracts:
            await create_notification_logs(contracts, admins)
        else:
            print("   ⚠️  Skipped notification logs (no contracts)")
    except Exception as e:
        print(f"❌ Notification logs failed: {e}")
        errors.append(f"Notification logs: {e}")

    # 11. Recurring schedules
    try:
        await create_recurring_schedules()
    except Exception as e:
        print(f"❌ Recurring schedules failed: {e}")
        errors.append(f"Recurring schedules: {e}")

    # 12. Workflow events
    try:
        if contracts:
            await create_workflow_events(contracts)
        else:
            print("   ⚠️  Skipped workflow events (no contracts)")
    except Exception as e:
        print(f"❌ Workflow events failed: {e}")
        errors.append(f"Workflow events: {e}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    if errors:
        print(f"⚠️  Completed with {len(errors)} error(s):")
        for err in errors:
            print(f"   - {err}")
    else:
        print("✅ Phase 5F seed completed successfully!")
    print(f"⏱  Time: {elapsed:.1f}s")
    print("=" * 60)
    print("\n📋 Default login credentials (password: Test@123)")
    print("   SuperAdmin : superadmin@phase5.com")
    print("   Admin      : alice.morgan@phase5.com")
    print("   Site Mgr   : david.park@phase5.com")


if __name__ == "__main__":
    asyncio.run(main())
