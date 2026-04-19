# seed_mongo.py

import asyncio
import os
from passlib.context import CryptContext
from backend.database import init_db, get_next_uid
from backend.models import (
    Admin, Employee, Site, Designation, 
    Attendance, Schedule, Counter
)

# --- CONFIGURATION ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 1. DEFINE THE "BRAIN" (Roles & Permissions) ---
# We denormalize this. Instead of a 'roles' table, we copy permissions 
# into the Admin document. This makes the JWT token generation instant.

ALL_PERMISSIONS = [
    'employee:view_all', 'employee:view_assigned', 
    'employee:create', 'employee:edit', 'employee:delete',
    'attendance:update', 
    'payslip:generate', 'payslip:view_all',
    'admin:view_all', 'admin:create:manager', 'admin:create:admin', 'admin:edit', 'admin:delete',
    'site:create', 'site:view', 'site:edit', 'site:delete',
    'schedule:edit', 'schedule:view_assigned'
]

ROLE_MAP = {
    'SuperAdmin': ALL_PERMISSIONS,
    'Admin': [
        'employee:view_all', 'employee:create', 'employee:edit', 'employee:delete',
        'attendance:update', 'payslip:generate', 'payslip:view_all',
        'admin:view_all', 'admin:create:manager', 'admin:edit', 'admin:delete',
        'site:create', 'site:view', 'site:edit', 'site:delete',
        'schedule:edit', 'schedule:view_assigned'
    ],
    'Site Manager': [
        'employee:view_assigned',
        'attendance:update',
        'site:view',
        'schedule:edit',
        'schedule:view_assigned'
    ]
}

# --- 2. SAMPLE DATA ---

SITES_DATA = [
    {"name": "Main Office", "location": "123 Capital City, Kuwait"},
    {"name": "West-Side Warehouse", "location": "456 Industrial Area, Kuwait"}
]

EMPLOYEES_DATA = [
    {'name': 'Nachiappan', 'designation': 'Driver', 'basic_salary': 200.0, 'allowance': 60.0, 'standard_work_days': 28},
    {'name': 'Noufar', 'designation': 'Labour', 'basic_salary': 200.0, 'allowance': 0.0, 'standard_work_days': 28},
    {'name': 'Thirupathy', 'designation': 'Labour', 'basic_salary': 210.0, 'allowance': 0.0, 'standard_work_days': 28},
    {'name': 'Sarath Kumar', 'designation': 'Welder', 'basic_salary': 250.0, 'allowance': 25.0, 'standard_work_days': 26},
]

ADMINS_DATA = [
    {"email": "admin@company.com", "name": "Super Administrator", "pass": "password", "desig": "Managing Director", "role": "SuperAdmin"},
    {"email": "admin.user@company.com", "name": "General Admin", "pass": "admin_password", "desig": "HR Manager", "role": "Admin"},
    {"email": "manager@company.com", "name": "Site Manager", "pass": "manager_password", "desig": "Site Supervisor", "role": "Site Manager"},
]

async def seed():
    print("🌱 Starting MongoDB Seeding...")
    
    # 1. Connect to DB
    await init_db()

    # --- ADD THIS LINE ---
    # This forces a hard reset of the database structure
    await Admin.get_pymongo_collection().database.client.drop_database("payroll_db")
    print("   💥 Hard Reset: Dropped 'payroll_db'")
    
    # Re-init is sometimes needed after a drop to ensure collections exist
    await init_db() 

    # 2. CLEAR EVERYTHING (Wipe Slate)
    print("   ⚠️  Clearing existing data...")
    await Admin.delete_all()
    await Employee.delete_all()
    await Site.delete_all()
    await Designation.delete_all()
    await Attendance.delete_all()
    await Schedule.delete_all()
    await Counter.delete_all() # Reset IDs to 1
    
    # 3. SEED SITES (We need their IDs for Managers)
    print("   🏗️  Creating Sites...")
    site_name_to_uid = {}
    
    for site_data in SITES_DATA:
        uid = await get_next_uid("sites")
        site = Site(
            uid=uid,
            name=site_data["name"],
            location=site_data["location"]
        )
        await site.insert()
        site_name_to_uid[site.name] = uid
        print(f"      - Created Site [{uid}]: {site.name}")

    # 4. SEED ADMINS
    print("   🛡️  Creating Admins...")
    for admin_data in ADMINS_DATA:
        uid = await get_next_uid("admins")
        hashed_pw = pwd_context.hash(admin_data["pass"])
        role_perms = ROLE_MAP.get(admin_data["role"], [])
        
        # Logic: Assign 'Site Manager' to 'West-Side Warehouse'
        assigned_sites = []
        if admin_data["role"] == "Site Manager":
            if "West-Side Warehouse" in site_name_to_uid:
                assigned_sites.append(site_name_to_uid["West-Side Warehouse"])
        
        admin = Admin(
            uid=uid,
            email=admin_data["email"],
            hashed_password=hashed_pw,
            full_name=admin_data["name"],
            designation=admin_data["desig"],
            role=admin_data["role"],
            permissions=role_perms,         # Injecting Permissions directly
            assigned_site_uids=assigned_sites # Injecting Site IDs directly
        )
        await admin.insert()
        print(f"      - Created {admin_data['role']} [{uid}]: {admin.email}")

    # 5. SEED EMPLOYEES
    print("   👷 Creating Employees...")
    for emp_data in EMPLOYEES_DATA:
        uid = await get_next_uid("employees")
        emp = Employee(
            uid=uid,
            name=emp_data["name"],
            designation=emp_data["designation"],
            basic_salary=emp_data["basic_salary"],
            allowance=emp_data["allowance"],
            standard_work_days=emp_data["standard_work_days"],
            # Example of Dynamic Data Usage:
            specs={"uniform_issued": False, "skills": ["Basic Safety"]}
        )
        await emp.insert()
        print(f"      - Created Employee [{uid}]: {emp.name}")

    # 6. SEED DESIGNATIONS (Optional, for dropdowns)
    print("   🏷️  Creating Designations...")
    unique_desigs = set(e['designation'] for e in EMPLOYEES_DATA)
    for title in unique_desigs:
        uid = await get_next_uid("designations")
        await Designation(uid=uid, title=title).insert()

    print("\n✅ Seeding Complete! You can now log in.")

if __name__ == "__main__":
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(seed())