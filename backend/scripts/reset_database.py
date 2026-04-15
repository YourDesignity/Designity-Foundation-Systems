"""
Database reset script for Montreal Management System.
Wipes ALL collections and starts fresh.
"""
import asyncio
import platform
import os
from pathlib import Path
from urllib.parse import quote_plus
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_mongo_connection_url() -> str:
    current_os = platform.system()
    if current_os == "Windows":
        return os.getenv("MONGO_URL", "mongodb://localhost:27017")
    else:
        db_user = os.getenv("DB_USER", "destiny_mind")
        db_pass = os.getenv("DB_PASS", "iamironman")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "27017")
        auth_db = os.getenv("AUTH_SOURCE", "destiny-neural-memory")
        return f"mongodb://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/?authSource={auth_db}"


async def reset_database() -> None:
    """Wipe ALL collections and start fresh."""
    mongo_url = get_mongo_connection_url()
    db_name = os.getenv("DB_NAME", "payroll_db")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print(f"🔥 Connecting to database: {db_name}")
    print("🔥 DROPPING ALL COLLECTIONS...")

    collections = await db.list_collection_names()
    if not collections:
        print("  ℹ️  No collections found — database is already empty.")
    else:
        for coll in collections:
            await db[coll].drop()
            print(f"  ✅ Dropped: {coll}")

    print("\n✅ Database reset complete! Ready for fresh start.")
    client.close()


if __name__ == "__main__":
    asyncio.run(reset_database())
