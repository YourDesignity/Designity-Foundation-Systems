import os
from pathlib import Path
from urllib.parse import quote_plus
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv

# 1. IMPORTS: Models
from backend.models import (
    Counter, Admin, Employee, Site, Attendance, Schedule, Designation, 
    Overtime, Deduction, DutyAssignment, Vehicle, TripLog, 
    MaintenanceLog, FuelLog, VehicleExpense, ContractSpec, InventoryItem,
    Invoice, Conversation, Message, ManagerProfile,
    ManagerAttendanceConfig, ManagerAttendance, CompanySettings,
    # NEW: Project Workflow System (Phase 1)
    Project, EmployeeAssignment, TemporaryAssignment,
    # NEW: Material Management
    Material, Supplier, PurchaseOrder, MaterialMovement,
    # NEW: Role-Based Labour Contracts (Phase 1)
    DailyRoleFulfillment,
)
# Contract types (Phase 5A) – registered individually so Beanie can
# resolve the polymorphic ``_type`` discriminator for each sub-class.
from backend.models.contracts import (
    LabourContract,
    RoleBasedContract,
    GoodsContract,
    HybridContract,
)
# Phase 5D: Workflow audit trail
from backend.models.workflow_history import (
    WorkflowHistory,
    ApprovalRequest,
    WorkflowEvent,
)
# Phase 5E: Scheduling & automation
from backend.models.schedules import (
    ScheduledJob,
    NotificationLog,
    RecurringSchedule,
)
# Module settings (singleton)
from backend.models.module_settings import GlobalModuleSettings
# Audit trail
from backend.models.audit_log import AuditLog

# Load Environment Variables
env_path = Path("./backend/.env") 
load_dotenv(dotenv_path=env_path)

DB_NAME = os.getenv("DB_NAME", "payroll_db")

def get_mongo_connection_url():
    auth_enabled = os.getenv("DB_AUTH_ENABLED", "false").strip().lower() == "true"
    if auth_enabled:
        db_user = os.getenv("DB_USER", "destiny_mind")
        db_pass = os.getenv("DB_PASS", "iamironman")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "27017")
        auth_db = os.getenv("AUTH_DB", "admin")
        # Add directConnection=true to bypass replica set hostname resolution issues on Linux/Docker
        # This prevents "AutoReconnect: container_id:27017 [Errno -3] Temporary failure in name resolution"
        url = f"mongodb://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/?authSource={auth_db}&directConnection=true"
        print("🔐 DB connection mode: AUTH ENABLED (Linux/Production)")
        return url
    else:
        url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        print("🪟 DB connection mode: NO AUTH (Windows/Local Dev)")
        return url

MONGO_URL = get_mongo_connection_url()

async def init_db():
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        await init_beanie(
            database=client[DB_NAME],
            document_models=[
                Counter, Admin, Employee, Site, Attendance, Schedule, Designation, 
                Overtime, Deduction, DutyAssignment, Vehicle, TripLog, 
                MaintenanceLog, FuelLog, VehicleExpense, ContractSpec, InventoryItem,
                Invoice, Conversation, Message, ManagerProfile,
                ManagerAttendanceConfig, ManagerAttendance, CompanySettings,
                # NEW: Project Workflow System (Phase 1)
                Project, EmployeeAssignment, TemporaryAssignment,
                # NEW: Material Management
                Material, Supplier, PurchaseOrder, MaterialMovement,
                # NEW: Role-Based Labour Contracts (Phase 1)
                DailyRoleFulfillment,
                # Contract types (Phase 5A) – replaces the old monolithic Contract
                LabourContract,
                RoleBasedContract,
                GoodsContract,
                HybridContract,
                # Phase 5D: Workflow audit trail
                WorkflowHistory,
                ApprovalRequest,
                WorkflowEvent,
                # Phase 5E: Scheduling & automation
                ScheduledJob,
                NotificationLog,
                RecurringSchedule,
                # Module settings (singleton)
                GlobalModuleSettings,
                # Audit trail
                AuditLog,
            ]
        )
        print(f"✅ Connected to MongoDB at {DB_NAME}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise e

async def get_next_uid(collection_name: str) -> int:
    counter = await Counter.find_one(Counter.collection_name == collection_name)
    if not counter:
        counter = Counter(collection_name=collection_name, current_uid=0)
        await counter.create()
    await counter.inc({Counter.current_uid: 1})
    return counter.current_uid
