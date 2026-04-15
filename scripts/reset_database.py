#!/usr/bin/env python3
"""
MongoDB Database Reset Script for Linux
Wipes, resets counters, and optionally seeds default data.

Usage:
    python scripts/reset_database.py --full       # Full reset with seed data
    python scripts/reset_database.py --clean      # Clean only (no seed)
    python scripts/reset_database.py --backup     # Backup only (no reset)
    python scripts/reset_database.py --full --yes # Skip confirmation prompt
"""

import asyncio
import json
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import argparse

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so backend package can be imported
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# Load .env from backend/
load_dotenv(dotenv_path=PROJECT_ROOT / "backend" / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/db_reset.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MongoDB Configuration
# ---------------------------------------------------------------------------
CURRENT_OS = platform.system()


def get_mongo_connection_url() -> str:
    if CURRENT_OS == "Windows":
        return os.getenv("MONGO_URL", "mongodb://localhost:27017")
    else:
        db_user = os.getenv("DB_USER", "destiny_mind")
        db_pass = os.getenv("DB_PASS", "iamironman")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "27017")
        auth_db = os.getenv("AUTH_SOURCE", "destiny-neural-memory")
        return (
            f"mongodb://{quote_plus(db_user)}:{quote_plus(db_pass)}"
            f"@{db_host}:{db_port}/?authSource={auth_db}"
        )


MONGO_URI = get_mongo_connection_url()
DB_NAME = os.getenv("DB_NAME", "payroll_db")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Counter names that map to collections tracked with auto-increment UIDs
COUNTER_NAMES = [
    "employees",
    "admins",
    "sites",
    "schedules",
    "attendance",
    "projects",
    "contracts",
    "invoices",
    "vehicles",
    "managers",
    "designations",
    "employee_assignments",
    "temporary_assignments",
]


# ---------------------------------------------------------------------------
# DatabaseResetter
# ---------------------------------------------------------------------------

class DatabaseResetter:
    def __init__(self):
        self.client = None
        self.db = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to MongoDB and verify the connection."""
        try:
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            await self.client.admin.command("ping")
            logger.info(f"✅ Connected to MongoDB: {DB_NAME}")
            return True
        except Exception as exc:
            logger.error(f"❌ Failed to connect to MongoDB: {exc}")
            return False

    async def close(self):
        """Close the database connection."""
        if self.client:
            self.client.close()
            logger.info("🔌 Database connection closed")

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    async def backup_database(self) -> str | None:
        """Export every collection to a timestamped JSON file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"db_backup_{timestamp}.json"

            collections = await self.db.list_collection_names()
            backup_data: dict = {}

            for coll_name in collections:
                docs = await self.db[coll_name].find().to_list(length=None)
                for doc in docs:
                    doc["_id"] = str(doc["_id"])
                backup_data[coll_name] = docs

            with open(backup_path, "w") as fh:
                json.dump(backup_data, fh, indent=2, default=str)

            logger.info(f"✅ Backup created: {backup_path}")
            return str(backup_path)
        except Exception as exc:
            logger.error(f"❌ Backup failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Drop collections
    # ------------------------------------------------------------------

    async def drop_all_collections(self) -> bool:
        """Drop every collection in the database."""
        try:
            collections = await self.db.list_collection_names()
            logger.info(f"🗑️  Dropping {len(collections)} collection(s)...")

            for coll_name in collections:
                await self.db[coll_name].drop()
                logger.info(f"   ✓ Dropped: {coll_name}")

            logger.info("✅ All collections dropped")
            return True
        except Exception as exc:
            logger.error(f"❌ Failed to drop collections: {exc}")
            return False

    # ------------------------------------------------------------------
    # Counter reset
    # ------------------------------------------------------------------

    async def reset_counters(self) -> bool:
        """Reset all UID counters to 0 (next insert will get uid=1)."""
        try:
            counters_col = self.db["counters"]
            logger.info("🔢 Resetting UID counters...")

            for name in COUNTER_NAMES:
                await counters_col.update_one(
                    {"collection_name": name},
                    {"$set": {"current_uid": 0}},
                    upsert=True,
                )
                logger.info(f"   ✓ Reset counter: {name}")

            logger.info("✅ All counters reset to 0")
            return True
        except Exception as exc:
            logger.error(f"❌ Failed to reset counters: {exc}")
            return False

    # ------------------------------------------------------------------
    # Seed default data
    # ------------------------------------------------------------------

    async def seed_default_data(self) -> bool:
        """Insert minimum default data required to operate the system."""
        try:
            logger.info("🌱 Seeding default data...")

            now = datetime.now()

            # 1. SuperAdmin ------------------------------------------------
            admins_col = self.db["admins"]
            default_admin = {
                "uid": 1,
                "email": "admin@montreal.com",
                "hashed_password": pwd_context.hash("admin123"),
                "full_name": "System Administrator",
                "designation": "SuperAdmin",
                "role": "SuperAdmin",
                "permissions": ["*"],
                "assigned_site_uids": [],
                "has_manager_profile": False,
                "is_active": True,
                "specs": {},
                "created_at": now,
                "updated_at": now,
            }
            await admins_col.insert_one(default_admin)
            logger.info(
                "   ✓ Created default SuperAdmin "
                "(admin@montreal.com / admin123)"
            )

            # 2. Company Settings ------------------------------------------
            settings_col = self.db["company_settings"]
            default_settings = {
                "uid": 1,
                "normal_overtime_multiplier": 1.25,
                "offday_overtime_multiplier": 1.5,
                "standard_hours_per_day": 8,
                "enable_absence_deduction": True,
                "enable_local_storage": True,
                "use_employee_name_in_filename": True,
                "auto_generate_project_codes": True,
                "project_code_prefix": "PRJ",
                "auto_generate_contract_codes": True,
                "contract_code_prefix": "CNT",
                "auto_generate_site_codes": True,
                "site_code_prefix": "SITE",
                "contract_expiry_warning_days": 30,
                "default_external_worker_daily_rate": 15.0,
                "default_external_worker_hourly_rate": 1.875,
                "updated_at": now,
            }
            await settings_col.insert_one(default_settings)
            logger.info("   ✓ Created default company settings")

            # 3. Default Designations --------------------------------------
            designations_col = self.db["designations"]
            designation_titles = [
                "Project Manager", "Site Engineer", "Foreman",
                "Laborer", "Skilled Worker", "Driver", "Welder",
            ]
            default_designations = [
                {"uid": i, "title": title, "is_active": True, "specs": {}, "created_at": now, "updated_at": now}
                for i, title in enumerate(designation_titles, start=1)
            ]
            await designations_col.insert_many(default_designations)
            logger.info(
                f"   ✓ Created {len(default_designations)} default designations"
            )

            # 4. Sync counters to match seeded UIDs ------------------------
            counters_col = self.db["counters"]
            counter_updates = {
                "admins": 1,
                "designations": len(default_designations),
            }
            for coll_name, value in counter_updates.items():
                await counters_col.update_one(
                    {"collection_name": coll_name},
                    {"$set": {"current_uid": value}},
                    upsert=True,
                )

            logger.info("✅ Default data seeded successfully")
            return True
        except Exception as exc:
            logger.error(f"❌ Failed to seed data: {exc}")
            return False


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

async def main(args) -> None:
    resetter = DatabaseResetter()

    if not await resetter.connect():
        logger.error("❌ Cannot proceed without database connection")
        sys.exit(1)

    try:
        # ----------------------------------------------------------------
        # Backup-only mode
        # ----------------------------------------------------------------
        if args.backup:
            logger.info("📦 BACKUP MODE")
            await resetter.backup_database()
            return

        # ----------------------------------------------------------------
        # Confirmation prompt
        # ----------------------------------------------------------------
        if not args.yes:
            print("\n⚠️  WARNING: This will DELETE ALL DATA in the database!")
            print(f"   Database : {DB_NAME}")
            print(f"   URI      : {MONGO_URI}")
            response = input("\nAre you sure you want to continue? (yes/no): ")
            if response.strip().lower() != "yes":
                logger.info("❌ Reset cancelled by user")
                return

        # ----------------------------------------------------------------
        # Auto-backup before destructive actions
        # ----------------------------------------------------------------
        logger.info("📦 Creating backup before reset...")
        backup_path = await resetter.backup_database()
        if backup_path:
            logger.info(f"✅ Backup saved to: {backup_path}")
        else:
            logger.warning("⚠️  Backup failed — proceeding without backup")

        # ----------------------------------------------------------------
        # Drop all collections
        # ----------------------------------------------------------------
        if not await resetter.drop_all_collections():
            logger.error("❌ Failed to drop collections — aborting")
            sys.exit(1)

        # ----------------------------------------------------------------
        # Reset counters
        # ----------------------------------------------------------------
        if not await resetter.reset_counters():
            logger.error("❌ Failed to reset counters — aborting")
            sys.exit(1)

        # ----------------------------------------------------------------
        # Seed data (--full only)
        # ----------------------------------------------------------------
        if args.full:
            if not await resetter.seed_default_data():
                logger.error("❌ Failed to seed default data")
                sys.exit(1)

        # ----------------------------------------------------------------
        # Done
        # ----------------------------------------------------------------
        logger.info("\n🎉 DATABASE RESET COMPLETE!")
        if args.full:
            logger.info("📧 Default Admin : admin@montreal.com")
            logger.info("🔑 Default Password : admin123")

    except Exception as exc:
        logger.error(f"❌ Reset failed unexpectedly: {exc}")
        sys.exit(1)
    finally:
        await resetter.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset the Montreal MongoDB database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full reset: drop all data, reset counters, then seed default data",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean reset: drop all data and reset counters (no seed data)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a JSON backup only — does not touch the database",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the interactive confirmation prompt (use in automation)",
    )

    args = parser.parse_args()

    # Default to clean mode when no mode is specified
    if not (args.full or args.clean or args.backup):
        args.clean = True

    asyncio.run(main(args))
