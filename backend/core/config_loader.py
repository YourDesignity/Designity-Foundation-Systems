# backend/core/config_loader.py
import json
import os
from typing import List, Dict, Optional

# Load the JSON file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/roles.json")

with open(CONFIG_PATH, "r") as f:
    _ROLES_DATA = json.load(f)["roles"]

class RoleConfig:
    @staticmethod
    def get_role_by_id(legacy_id: int) -> Optional[Dict]:
        """Finds role config based on the integer ID (1, 2, 3)"""
        for slug, data in _ROLES_DATA.items():
            if data["legacy_id"] == legacy_id:
                return data
        return None

    @staticmethod
    def get_role_by_name(db_name: str) -> Optional[Dict]:
        """Finds role config based on the DB string ('SuperAdmin')"""
        for slug, data in _ROLES_DATA.items():
            if data["db_name"] == db_name:
                return data
        return None
    
    @staticmethod
    def get_id_from_name(db_name: str) -> int:
        role = RoleConfig.get_role_by_name(db_name)
        return role["legacy_id"] if role else 0

    @staticmethod
    def get_perms(db_name: str) -> List[str]:
        role = RoleConfig.get_role_by_name(db_name)
        return role.get("permissions", []) if role else []