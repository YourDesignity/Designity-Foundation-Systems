"""
Montreal Test Data Injection Script
=====================================
Populates the entire Montreal database with realistic, interconnected test data
for thorough testing of all application features.

Usage:
    python -m backend.scripts.inject_test_data

WARNING: NEVER run against a production database!
"""

import asyncio
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Bootstrap path so script can be run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from faker import Faker
from passlib.context import CryptContext

from backend.database import init_db, get_next_uid, DB_NAME
from backend.models import (
    Admin, Employee, Site, Designation,
    Attendance, Overtime, Deduction,
    Vehicle, FuelLog, MaintenanceLog,
    Invoice, InvoiceItem,
    Conversation, Message,
    Project, Contract, EmployeeAssignment, TemporaryAssignment,
    Counter,
)
from backend.config.permissions import get_role_permissions

# =============================================================================
# CONFIGURATION  tweak counts/ranges here
# =============================================================================

DEFAULT_PASSWORD = "Test@123"

NUM_EMPLOYEES = 52
NUM_PROJECTS = 10
NUM_VEHICLES = 15
NUM_FUEL_LOGS = 110
NUM_MAINTENANCE_LOGS = 52
NUM_ATTENDANCE_DAYS = 30       # look-back window in days
NUM_INVOICES = 32
NUM_MESSAGES = 55
NUM_TEMP_ASSIGNMENTS = 22

DESIGNATIONS = [
    ("Carpenter",    22, 30),
    ("Electrician",  28, 38),
    ("Welder",       25, 35),
    ("Painter",      18, 26),
    ("Helper",       15, 20),
    ("Foreman",      32, 42),
    ("Supervisor",   35, 45),
    ("Plumber",      22, 32),
    ("Mason",        20, 28),
    ("Driver",       18, 25),
]

PROJECT_NAMES = [
    "Downtown Office Complex",
    "Harbor Warehouse Renovation",
    "Northside Residential Tower",
    "Industrial Factory Fit-Out",
    "Lakeside Retail Storefront",
    "City Hospital Wing Extension",
    "Westpark School Campus",
    "Central Parking Structure",
    "Riverside Sports Facility",
    "Grandview Hotel Refurbishment",
]

CLIENT_COMPANIES = [
    "Al-Mansour Holdings",
    "Gulf Construction Corp",
    "Downtown Developers Inc.",
    "Harbor Realty Partners",
    "CityBuild International",
    "Prestige Property Group",
    "Skyline Projects Ltd.",
    "Meridian Infrastructure",
    "Orion Building Solutions",
    "Atlas Construction LLC",
]

VEHICLE_SPECS = [
    ("Toyota",        "Hilux",        "Pickup Truck"),
    ("Ford",          "Transit",      "Van"),
    ("Nissan",        "Patrol",       "SUV"),
    ("Mercedes-Benz", "Sprinter",     "Van"),
    ("Toyota",        "Land Cruiser", "SUV"),
    ("Mitsubishi",    "L200",         "Pickup Truck"),
    ("Ford",          "F-150",        "Pickup Truck"),
    ("Hino",          "300 Series",   "Light Truck"),
    ("Isuzu",         "D-Max",        "Pickup Truck"),
    ("Volkswagen",    "Transporter",  "Van"),
    ("Chevrolet",     "Express",      "Van"),
    ("Kia",           "Bongo",        "Van"),
    ("Hyundai",       "H-350",        "Van"),
    ("RAM",           "1500",         "Pickup Truck"),
    ("Suzuki",        "Carry",        "Mini Truck"),
]

MAINTENANCE_TYPES = [
    "Oil Change",
    "Tire Rotation",
    "Tire Replacement",
    "Brake Service",
    "Air Filter Replacement",
    "Battery Replacement",
    "Transmission Service",
    "AC Service",
    "General Inspection",
    "Engine Repair",
]

ADMIN_MESSAGES = [
    "Reminder: Weekly safety meeting tomorrow at 9 AM.",
    "All site managers: please submit attendance reports by Friday.",
    "New safety guidelines have been uploaded to the portal.",
    "Public holiday next Monday - adjust schedules accordingly.",
    "Monthly payroll processing will be delayed by one day.",
    "Please ensure all vehicles have been inspected before dispatch.",
    "Project status updates are due by end of week.",
    "New contract signed - details shared in the project portal.",
    "Reminder: Document all overtime hours for this month.",
    "Site managers: ensure headcounts are accurate and up to date.",
    "Emergency contact list has been updated in the system.",
    "Vehicle maintenance schedules are due for review.",
]

# =============================================================================
# UTILITIES
# =============================================================================

fake = Faker("en_US")
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hashed(plain: str) -> str:
    return pwd_ctx.hash(plain)


def to_date_only(dt: datetime) -> datetime:
    """Strip time component from datetime, returning midnight (00:00:00)."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def rand_date_between(start: datetime, end: datetime) -> datetime:
    delta = max(0, (end - start).days)
    result = start + timedelta(days=random.randint(0, delta))
    return to_date_only(result)


def now() -> datetime:
    return datetime.now()


def days_ago(n: int) -> datetime:
    return now() - timedelta(days=n)


def days_from_now(n: int) -> datetime:
    return now() + timedelta(days=n)


def fmt_date(dt: datetime) -> str:
    """Format date as YYYY-MM-DD string."""
    return dt.strftime("%Y-%m-%d")


# =============================================================================
# SAFETY CHECK
# =============================================================================

def safety_check() -> bool:
    """Refuse to run if DB_NAME looks like a production database."""
    db_lower = DB_NAME.lower()
    if any(kw in db_lower for kw in ("prod", "production", "live", "real")):
        print(f"\n SAFETY BLOCK: DB_NAME=\'{DB_NAME}\' looks like PRODUCTION!")
        print("   Refusing to run. Rename your test DB or set DB_NAME env var.\n")
        return False
    return True


# =============================================================================
# ADMIN CREATION
# =============================================================================

ADMINS_SPEC = [
    {
        "email": "admin@montreal.com",
        "full_name": "Super Administrator",
        "designation": "Managing Director",
        "role": "SuperAdmin",
    },
    {
        "email": "john.smith@montreal.com",
        "full_name": "John Smith",
        "designation": "Operations Manager",
        "role": "Admin",
    },
    {
        "email": "sarah.johnson@montreal.com",
        "full_name": "Sarah Johnson",
        "designation": "HR Manager",
        "role": "Admin",
    },
    {
        "email": "mike.wilson@montreal.com",
        "full_name": "Mike Wilson",
        "designation": "Site Supervisor",
        "role": "Site Manager",
    },
    {
        "email": "emily.davis@montreal.com",
        "full_name": "Emily Davis",
        "designation": "Site Supervisor",
        "role": "Site Manager",
    },
]


async def create_admins() -> list:
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
            phone=fake.numerify("+1-###-###-####"),
        )
        await admin.insert()
        admins.append(admin)
    return admins


# =============================================================================
# EMPLOYEE CREATION
# =============================================================================

async def create_employees(managers: list) -> list:
    """Create 50+ realistic employees across various designations."""
    employees = []

    # Build pool: at least 3 per designation, then pad randomly
    designation_pool = []
    for desig_tuple in DESIGNATIONS:
        designation_pool.extend([desig_tuple] * 3)
    while len(designation_pool) < NUM_EMPLOYEES:
        designation_pool.append(random.choice(DESIGNATIONS))
    random.shuffle(designation_pool)
    designation_pool = designation_pool[:NUM_EMPLOYEES]

    manager_uids = [m.uid for m in managers if m.role == "Site Manager"]
    two_years_ago = days_ago(730)

    for desig, min_rate, max_rate in designation_pool:
        uid = await get_next_uid("employees")
        hourly = round(random.uniform(min_rate, max_rate), 2)
        monthly = round(hourly * 8 * 26, 2)
        join_date = rand_date_between(two_years_ago, days_ago(30))
        status = "Active" if random.random() > 0.08 else "Inactive"
        manager_id = random.choice(manager_uids) if manager_uids else None

        emp = Employee(
            uid=uid,
            name=fake.name(),
            designation=desig,
            status=status,
            employee_type="Company",
            basic_salary=monthly,
            allowance=round(random.uniform(50, 300), 2),
            standard_work_days=26,
            default_hourly_rate=hourly,
            date_of_joining=join_date,
            phone_kuwait=fake.numerify("+965-########"),
            phone_home_country=fake.phone_number()[:20],
            emergency_contact_name=fake.name(),
            emergency_contact_number=fake.phone_number()[:20],
            manager_id=manager_id,
            nationality=random.choice(
                ["Indian", "Pakistani", "Egyptian", "Filipino", "Kuwaiti", "British"]
            ),
            availability_status="Available",
        )
        await emp.insert()
        employees.append(emp)

    return employees


async def create_designations(employees: list) -> None:
    """Seed unique designations from employee designations."""
    unique = {e.designation for e in employees}
    for title in unique:
        uid = await get_next_uid("designations")
        try:
            await Designation(uid=uid, title=title).insert()
        except Exception:
            pass  # Already exists (unique index)


# =============================================================================
# PROJECTS, CONTRACTS, SITES
# =============================================================================

async def create_projects_contracts_sites(admins: list) -> tuple:
    """
    Create Projects then Contracts then Sites in dependency order.
    Returns (projects, contracts, sites).
    """
    projects = []
    contracts = []
    sites = []

    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])
    site_managers = [a for a in admins if a.role == "Site Manager"]

    two_years_ago = days_ago(730)
    site_idx = 0

    for p_idx in range(NUM_PROJECTS):
        proj_name = PROJECT_NAMES[p_idx % len(PROJECT_NAMES)]
        client = CLIENT_COMPANIES[p_idx % len(CLIENT_COMPANIES)]
        proj_status = random.choices(
            ["Active", "Completed", "On Hold"],
            weights=[0.6, 0.3, 0.1],
        )[0]

        proj_uid = await get_next_uid("projects")
        proj_start = rand_date_between(two_years_ago, days_ago(60))

        project = Project(
            uid=proj_uid,
            project_code=f"PRJ-{proj_uid:03d}",
            project_name=proj_name,
            client_name=client,
            client_contact=fake.name(),
            client_email=fake.company_email(),
            description=f"{proj_name} for {client}. Full construction and fit-out.",
            status=proj_status,
            created_by_admin_id=super_admin.uid,
        )
        await project.insert()
        projects.append(project)

        # 1-3 contracts per project
        num_contracts = random.randint(1, 3)
        for c_idx in range(num_contracts):
            cnt_uid = await get_next_uid("contracts")
            c_start = rand_date_between(proj_start, proj_start + timedelta(days=60))
            c_end_days = random.randint(60, 365)
            c_end = to_date_only(c_start + timedelta(days=c_end_days))

            # ~15% of contracts expiring very soon (triggers alerts)
            if random.random() < 0.15:
                c_end = to_date_only(days_from_now(random.randint(5, 25)))

            c_value = round(random.uniform(20_000, 200_000), 2)
            days_left = max(0, (c_end - now()).days)
            is_expiring = 0 < days_left <= 30
            is_expired = c_end < now()
            c_status = "Expired" if is_expired else (
                "Completed" if proj_status == "Completed" else "Active"
            )

            contract = Contract(
                uid=cnt_uid,
                contract_code=f"CON-{cnt_uid:04d}",
                contract_name=f"{proj_name} - Phase {c_idx + 1}",
                project_id=proj_uid,
                project_name=proj_name,
                start_date=c_start,
                end_date=c_end,
                contract_value=c_value,
                payment_terms=random.choice(["Monthly", "Milestone-based", "Upon Completion"]),
                status=c_status,
                duration_days=c_end_days,
                days_remaining=days_left,
                is_expiring_soon=is_expiring,
                created_by_admin_id=super_admin.uid,
            )
            await contract.insert()
            contracts.append(contract)
            project.contract_ids.append(cnt_uid)

            # 1-4 sites per contract
            num_sites = random.randint(1, 4)
            mgr = random.choice(site_managers) if site_managers else None
            suffixes = ["Block A", "Block B", "Floor 1", "Floor 2", "Wing East",
                        "Wing West", "North Zone", "South Zone", "Level 3"]

            for s_idx in range(num_sites):
                site_idx += 1
                s_uid = await get_next_uid("sites")
                s_status = "Active" if c_status == "Active" else random.choice(
                    ["Completed", "Inactive"]
                )
                suffix = suffixes[s_idx % len(suffixes)]

                site = Site(
                    uid=s_uid,
                    name=f"{proj_name} - {suffix} (S{site_idx:03d})",
                    location=f"{fake.street_address()}, Montreal, QC",
                    site_code=f"SITE-{s_uid:03d}",
                    project_id=proj_uid,
                    project_name=proj_name,
                    contract_id=cnt_uid,
                    contract_code=contract.contract_code,
                    assigned_manager_id=mgr.uid if mgr else None,
                    assigned_manager_name=mgr.full_name if mgr else None,
                    required_workers=random.randint(3, 15),
                    status=s_status,
                    start_date=c_start,
                    completion_date=c_end if s_status != "Active" else None,
                    description=f"Site {s_idx + 1} for {contract.contract_code}",
                )
                await site.insert()
                sites.append(site)

                contract.site_ids.append(s_uid)
                project.site_ids.append(s_uid)
                if mgr and s_uid not in mgr.assigned_site_uids:
                    mgr.assigned_site_uids.append(s_uid)

            await contract.save()

        project.total_sites = len(project.site_ids)
        await project.save()

    # Persist manager site assignments
    for mgr in site_managers:
        await mgr.save()

    return projects, contracts, sites


# =============================================================================
# EMPLOYEE ASSIGNMENTS
# =============================================================================

async def create_employee_assignments(employees: list, sites: list, admins: list) -> list:
    """Create 100+ employee assignments linking employees to active sites."""
    assignments = []
    active_sites = [s for s in sites if s.status == "Active"] or sites
    active_employees = [e for e in employees if e.status == "Active"] or employees
    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])

    assigned_count = 0
    for emp in active_employees:
        if assigned_count >= 100:
            break
        site = random.choice(active_sites)
        assign_uid = await get_next_uid("employee_assignments")
        start = rand_date_between(days_ago(180), days_ago(1))

        a = EmployeeAssignment(
            uid=assign_uid,
            employee_id=emp.uid,
            employee_name=emp.name,
            employee_type=emp.employee_type,
            employee_designation=emp.designation,
            assignment_type=random.choice(["Permanent", "Temporary"]),
            project_id=site.project_id,
            project_name=site.project_name,
            contract_id=site.contract_id,
            site_id=site.uid,
            site_name=site.name,
            manager_id=site.assigned_manager_id,
            manager_name=site.assigned_manager_name,
            assigned_date=start,
            assignment_start=start,
            assignment_end=(
                to_date_only(days_from_now(random.randint(30, 120))) if random.random() < 0.3 else None
            ),
            status="Active",
            created_by_admin_id=super_admin.uid,
        )
        await a.insert()
        assignments.append(a)

        if emp.uid not in site.assigned_employee_ids:
            site.assigned_employee_ids.append(emp.uid)
            site.assigned_workers = len(site.assigned_employee_ids)

        emp.is_currently_assigned = True
        emp.current_assignment_type = a.assignment_type
        emp.current_project_id = site.project_id
        emp.current_project_name = site.project_name
        emp.current_site_id = site.uid
        emp.current_site_name = site.name
        emp.current_manager_id = site.assigned_manager_id
        emp.current_manager_name = site.assigned_manager_name
        emp.current_assignment_start = to_date_only(start)
        emp.availability_status = "Assigned"
        assigned_count += 1

    for site in active_sites:
        await site.save()
    for emp in active_employees[:assigned_count]:
        await emp.save()

    return assignments


# =============================================================================
# TEMPORARY ASSIGNMENTS
# =============================================================================

async def create_temp_assignments(employees: list, sites: list, admins: list) -> list:
    """Create external/outsourced temporary worker assignments."""
    temp_assignments = []
    active_sites = [s for s in sites if s.status == "Active"] or sites
    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])

    outsourced_emps = []
    for _ in range(NUM_TEMP_ASSIGNMENTS):
        uid = await get_next_uid("employees")
        emp = Employee(
            uid=uid,
            name=fake.name(),
            designation=random.choice(["Helper", "Carpenter", "Electrician", "Mason"]),
            status="Active",
            employee_type="Outsourced",
            basic_salary=0.0,
            default_hourly_rate=round(random.uniform(50, 80), 2),
            standard_work_days=26,
            can_be_substitute=True,
            substitute_availability="available",
        )
        await emp.insert()
        outsourced_emps.append(emp)

    for emp in outsourced_emps:
        site = random.choice(active_sites)
        mgr_id = site.assigned_manager_id or admins[0].uid
        uid = await get_next_uid("temporary_assignments")
        days = random.randint(7, 28)
        start = rand_date_between(days_ago(60), days_ago(days + 1))
        end = to_date_only(start + timedelta(days=days))
        daily = round(random.uniform(50, 80) * 8, 2)

        ta = TemporaryAssignment(
            uid=uid,
            employee_id=emp.uid,
            employee_name=emp.name,
            employee_type="Outsourced",
            employee_designation=emp.designation,
            site_id=site.uid,
            site_name=site.name,
            project_id=site.project_id or 1,
            manager_id=mgr_id,
            start_date=start,
            end_date=end,
            total_days=days,
            rate_type="Daily",
            daily_rate=daily,
            hourly_rate=round(daily / 8, 2),
            status=random.choice(["Active", "Completed"]),
            created_by_admin_id=super_admin.uid,
        )
        await ta.insert()
        temp_assignments.append(ta)

    return temp_assignments


# =============================================================================
# VEHICLES
# =============================================================================

async def create_vehicles() -> list:
    """Create 15 company fleet vehicles."""
    vehicles = []
    used_plates: set = set()

    for make, model, vtype in VEHICLE_SPECS[:NUM_VEHICLES]:
        uid = await get_next_uid("vehicles")
        while True:
            plate = fake.bothify(text="?? ## ###", letters="ABCDEFGHJKLMNPQRSTUVWXYZ")
            if plate not in used_plates:
                used_plates.add(plate)
                break

        year = random.randint(2018, 2024)
        mileage = round(random.uniform(5_000, 120_000), 1)
        reg_exp = fmt_date(days_from_now(random.randint(30, 365)))
        ins_exp = fmt_date(days_from_now(random.randint(14, 365)))
        status = random.choices(
            ["Available", "In Use", "Under Maintenance"], weights=[0.6, 0.3, 0.1]
        )[0]

        v = Vehicle(
            uid=uid,
            model=f"{year} {make} {model}",
            plate=plate,
            type=vtype,
            status=status,
            current_mileage=mileage,
            registration_expiry=reg_exp,
            insurance_expiry=ins_exp,
        )
        await v.insert()
        vehicles.append(v)

    return vehicles


# =============================================================================
# FUEL LOGS
# =============================================================================

async def create_fuel_logs(vehicles: list) -> list:
    """Create 100+ fuel log entries over the last 90 days."""
    fuel_logs = []
    drivers = [fake.name() for _ in range(10)]

    for _ in range(NUM_FUEL_LOGS):
        v = random.choice(vehicles)
        uid = await get_next_uid("vehicle_fuel")
        log_date = rand_date_between(days_ago(90), now())
        liters = round(random.uniform(20, 80), 2)
        cost = round(liters * random.uniform(1.8, 2.5), 2)
        odometer = v.current_mileage + random.uniform(100, 5_000)

        fl = FuelLog(
            uid=uid,
            vehicle_uid=v.uid,
            vehicle_plate=v.plate,
            date=fmt_date(log_date),
            liters=liters,
            cost=cost,
            odometer=round(odometer, 1),
            filled_by=random.choice(drivers),
        )
        await fl.insert()
        fuel_logs.append(fl)

    return fuel_logs


# =============================================================================
# MAINTENANCE LOGS
# =============================================================================

async def create_maintenance_logs(vehicles: list) -> list:
    """Create 50+ maintenance records over the last year."""
    maint_logs = []

    for _ in range(NUM_MAINTENANCE_LOGS):
        v = random.choice(vehicles)
        uid = await get_next_uid("vehicle_maintenance")
        svc_date = rand_date_between(days_ago(365), now())
        next_due = svc_date + timedelta(days=random.randint(30, 180))
        cost = round(random.uniform(100, 2_000), 2)
        svc_type = random.choice(MAINTENANCE_TYPES)

        ml = MaintenanceLog(
            uid=uid,
            vehicle_uid=v.uid,
            vehicle_plate=v.plate,
            service_type=svc_type,
            cost=cost,
            service_date=fmt_date(svc_date),
            next_due_date=fmt_date(next_due),
            notes=f"{svc_type} performed at {v.current_mileage:,.0f} km.",
        )
        await ml.insert()
        maint_logs.append(ml)

    return maint_logs


# =============================================================================
# ATTENDANCE RECORDS
# =============================================================================

async def create_attendance(employees: list, sites: list) -> list:
    """Create 200+ attendance records for the last 30 days."""
    records = []
    active_employees = [e for e in employees if e.status == "Active"] or employees
    active_sites = [s for s in sites if s.status == "Active"] or sites
    target = 200
    created = 0

    for emp in active_employees:
        if created >= target:
            break
        site = random.choice(active_sites)
        for day_offset in range(NUM_ATTENDANCE_DAYS):
            if created >= target:
                break
            record_date = now() - timedelta(days=day_offset)
            weekday = record_date.weekday()
            # Higher presence chance on weekdays
            present_chance = 0.70 if weekday < 5 else 0.25
            if random.random() > present_chance:
                continue

            uid = await get_next_uid("attendance")
            ot_hours = random.choice([0, 0, 0, 1, 2]) if weekday < 5 else random.choice([0, 2, 4])

            att = Attendance(
                uid=uid,
                employee_uid=emp.uid,
                site_uid=site.uid,
                date=fmt_date(record_date),
                status="Present",
                shift="Morning",
                overtime_hours=ot_hours,
                recorded_at=record_date,
            )
            await att.insert()
            records.append(att)
            created += 1

    return records


# =============================================================================
# DEDUCTIONS
# =============================================================================

async def create_deductions(employees: list) -> list:
    """Create salary deductions for a sample of employees."""
    deductions = []
    sample = random.sample(employees, min(20, len(employees)))
    months = ["2026-02", "2026-03"]

    for emp in sample:
        for month in months:
            if random.random() > 0.5:
                continue
            uid = await get_next_uid("deductions")
            d = Deduction(
                uid=uid,
                employee_uid=emp.uid,
                pay_period=month,
                amount=round(random.uniform(20, 200), 2),
                reason=random.choice([
                    "Advance repayment",
                    "Uniform deduction",
                    "Late arrival fine",
                    "Equipment damage",
                    "Absence deduction",
                ]),
            )
            await d.insert()
            deductions.append(d)

    return deductions


# =============================================================================
# INVOICES
# =============================================================================

async def create_invoices(projects: list, contracts: list) -> list:
    """Create 30+ client invoices linked to projects."""
    invoices_list = []
    statuses = ["Paid", "Unpaid", "Overdue"]
    weights = [0.5, 0.3, 0.2]
    service_descriptions = [
        "Labour Services",
        "Equipment Rental",
        "Material Supply",
        "Supervision Fee",
        "Site Overhead",
        "Safety Equipment",
    ]

    for _ in range(NUM_INVOICES):
        project = random.choice(projects)
        uid = await get_next_uid("invoices")
        inv_date = rand_date_between(days_ago(180), now())
        due_date = inv_date + timedelta(days=random.randint(14, 45))
        status = random.choices(statuses, weights=weights)[0]
        if due_date < now() and status == "Unpaid":
            status = "Overdue"

        items = []
        total = 0.0
        for _ in range(random.randint(1, 4)):
            qty = round(random.uniform(1, 50), 1)
            rate = round(random.uniform(100, 2_000), 2)
            item_total = round(qty * rate, 2)
            total += item_total
            items.append(InvoiceItem(
                description=random.choice(service_descriptions),
                quantity=qty,
                unit_rate=rate,
                total=item_total,
            ))

        inv = Invoice(
            uid=uid,
            invoice_no=f"INV-{uid:04d}",
            project_uid=project.uid,
            client_name=project.client_name,
            date=fmt_date(inv_date),
            due_date=fmt_date(due_date),
            items=items,
            total_amount=round(total, 2),
            status=status,
        )
        await inv.insert()
        invoices_list.append(inv)

    return invoices_list


# =============================================================================
# MESSAGES AND CONVERSATIONS
# =============================================================================

async def create_messages(admins: list) -> list:
    """Create broadcast conversations and messages between admins."""
    messages = []
    if not admins:
        return messages

    super_admin = next((a for a in admins if a.role == "SuperAdmin"), admins[0])
    participant_ids = [a.uid for a in admins]
    participant_names = [a.full_name for a in admins]

    # Broadcast conversation
    conv_uid = await get_next_uid("conversations")
    conversation = Conversation(
        uid=conv_uid,
        conversation_type="broadcast_all",
        created_by_id=super_admin.uid,
        created_by_name=super_admin.full_name,
        created_by_role=super_admin.role,
        participant_ids=participant_ids,
        participant_names=participant_names,
        title="Broadcast: All Staff",
        last_message_at=now(),
        unread_count_map={str(a.uid): random.randint(0, 5) for a in admins},
    )
    await conversation.insert()

    # Messages
    msg_count = min(NUM_MESSAGES, len(ADMIN_MESSAGES) * 5)
    for _ in range(msg_count):
        sender = random.choice(admins)
        msg_uid = await get_next_uid("messages")
        ts = rand_date_between(days_ago(30), now())
        is_read = random.random() > 0.3

        msg = Message(
            uid=msg_uid,
            conversation_id=conv_uid,
            sender_id=sender.uid,
            sender_name=sender.full_name,
            sender_role=sender.role,
            sender_type="admin",
            content=random.choice(ADMIN_MESSAGES),
            timestamp=ts,
            read_by_ids=participant_ids if is_read else [sender.uid],
        )
        await msg.insert()
        messages.append(msg)

    return messages


# =============================================================================
# CLEAR ALL TEST DATA
# =============================================================================

async def clear_all_data() -> None:
    """Delete all records from all collections."""
    collections_to_clear = [
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
    for model in collections_to_clear:
        try:
            await model.delete_all()
        except Exception as e:
            print(f"   Warning: Could not clear {model.__name__}: {e}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main() -> None:
    t_start = time.monotonic()

    print()
    print("Montreal Test Data Injection Script")
    print("=" * 50)
    print()

    if not safety_check():
        sys.exit(1)

    print("Connecting to MongoDB...")
    await init_db()
    print(f"   Database: {DB_NAME}")
    print()

    answer = input(
        "WARNING: This will CLEAR existing data and inject test data.\n"
        "Continue? (yes/no): "
    ).strip().lower()
    if answer not in ("yes", "y"):
        print("Aborted.")
        return

    print()
    print("Creating test data...")
    print()

    errors = []

    # 1. Clear existing data
    await clear_all_data()

    # 2. Admins
    try:
        admins = await create_admins()
        managers = [a for a in admins if a.role == "Site Manager"]
        print(f"Created {len(admins)} Admins")
        for a in admins:
            print(f"   - {a.full_name} <{a.email}> ({a.role})")
    except Exception as e:
        errors.append(f"Admins: {e}")
        admins, managers = [], []

    # 3. Employees
    try:
        employees = await create_employees(managers)
        await create_designations(employees)
        active_count = sum(1 for e in employees if e.status == "Active")
        print(f"Created {len(employees)} Employees ({active_count} active)")
        desig_counts: dict = {}
        for e in employees:
            desig_counts[e.designation] = desig_counts.get(e.designation, 0) + 1
        for desig, cnt in sorted(desig_counts.items()):
            print(f"   - {desig}: {cnt}")
    except Exception as e:
        errors.append(f"Employees: {e}")
        employees = []

    # 4. Projects + Contracts + Sites
    try:
        projects, contracts, sites = await create_projects_contracts_sites(admins)
        active_c = sum(1 for c in contracts if c.status == "Active")
        expiring_c = sum(1 for c in contracts if c.is_expiring_soon)
        print(f"Created {len(projects)} Projects")
        print(
            f"Created {len(contracts)} Contracts "
            f"({active_c} active, {expiring_c} expiring soon)"
        )
        print(f"Created {len(sites)} Sites")
    except Exception as e:
        errors.append(f"Projects/Contracts/Sites: {e}")
        projects, contracts, sites = [], [], []

    # 5. Employee Assignments
    try:
        if employees and sites:
            assignments = await create_employee_assignments(employees, sites, admins)
            print(f"Created {len(assignments)} Employee Assignments")
        else:
            print("Skipped employee assignments (no employees or sites)")
            assignments = []
    except Exception as e:
        errors.append(f"Employee Assignments: {e}")
        assignments = []

    # 6. Temporary Assignments
    try:
        if sites:
            temp_assignments = await create_temp_assignments(employees, sites, admins)
            print(f"Created {len(temp_assignments)} Temporary Worker Assignments")
        else:
            temp_assignments = []
    except Exception as e:
        errors.append(f"Temporary Assignments: {e}")
        temp_assignments = []

    # 7. Vehicles
    try:
        vehicles = await create_vehicles()
        print(f"Created {len(vehicles)} Vehicles")
    except Exception as e:
        errors.append(f"Vehicles: {e}")
        vehicles = []

    # 8. Fuel Logs
    try:
        if vehicles:
            fuel_logs = await create_fuel_logs(vehicles)
            total_fuel_cost = sum(fl.cost for fl in fuel_logs)
            print(f"Created {len(fuel_logs)} Fuel Log entries (${total_fuel_cost:,.0f} total cost)")
        else:
            fuel_logs = []
    except Exception as e:
        errors.append(f"Fuel Logs: {e}")
        fuel_logs = []

    # 9. Maintenance Logs
    try:
        if vehicles:
            maint_logs = await create_maintenance_logs(vehicles)
            total_maint_cost = sum(ml.cost for ml in maint_logs)
            print(
                f"Created {len(maint_logs)} Maintenance Records "
                f"(${total_maint_cost:,.0f} total cost)"
            )
        else:
            maint_logs = []
    except Exception as e:
        errors.append(f"Maintenance Logs: {e}")
        maint_logs = []

    # 10. Attendance
    try:
        if employees and sites:
            attendance = await create_attendance(employees, sites)
            print(
                f"Created {len(attendance)} Attendance Records "
                f"(last {NUM_ATTENDANCE_DAYS} days)"
            )
        else:
            attendance = []
    except Exception as e:
        errors.append(f"Attendance: {e}")
        attendance = []

    # 11. Deductions
    try:
        if employees:
            deductions = await create_deductions(employees)
            print(f"Created {len(deductions)} Deduction Records")
        else:
            deductions = []
    except Exception as e:
        errors.append(f"Deductions: {e}")
        deductions = []

    # 12. Invoices
    try:
        if projects:
            invoices = await create_invoices(projects, contracts)
            total_billed = sum(inv.total_amount for inv in invoices)
            paid_count = sum(1 for inv in invoices if inv.status == "Paid")
            overdue_count = sum(1 for inv in invoices if inv.status == "Overdue")
            print(
                f"Created {len(invoices)} Invoices "
                f"(${total_billed:,.0f} billed, "
                f"{paid_count} paid, {overdue_count} overdue)"
            )
        else:
            invoices = []
    except Exception as e:
        errors.append(f"Invoices: {e}")
        invoices = []

    # 13. Messages
    try:
        if admins:
            msgs = await create_messages(admins)
            print(f"Created {len(msgs)} Messages")
        else:
            msgs = []
    except Exception as e:
        errors.append(f"Messages: {e}")
        msgs = []

    # Summary
    elapsed = time.monotonic() - t_start
    print()
    print("=" * 50)
    if errors:
        print(f"Completed with {len(errors)} error(s):")
        for err in errors:
            print(f"   - {err}")
    else:
        print("Test data injection complete!")

    print()
    print("Default Login Credentials:")
    print("   SuperAdmin:   admin@montreal.com")
    print("   Admin:        john.smith@montreal.com")
    print("   Site Manager: mike.wilson@montreal.com")
    print("   (Password: see DEFAULT_PASSWORD at top of this script)")
    print()
    print(f"Completed in {elapsed:.1f} seconds")
    print()


if __name__ == "__main__":
    asyncio.run(main())
