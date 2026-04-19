# backend/routers/roles.py

import logging
import json
from fastapi import APIRouter, Depends
from typing import List

# --- Imports ---
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger 

# --- Dynamic Config Import ---
# We import the raw data from the loader we created earlier.
# This ensures this endpoint always matches your 'roles.json' file.
from backend.core.config_loader import _ROLES_DATA 

router = APIRouter(
    prefix="/roles",
    tags=["Role Management"],
    dependencies=[Depends(get_current_active_user)]
)

# --- Initialize Logger ---
logger = setup_logger("RolesRouter", log_file="logs/roles_router.log", level=logging.DEBUG)

@router.get("/", response_model=List[dict])
async def get_all_roles():
    """
    Returns the list of Roles dynamically from the JSON configuration.
    This ensures the Frontend dropdowns match the Backend validation logic.
    """
    logger.info("ENDPOINT START: GET /roles")
    
    roles_list = []
    
    try:
        # Convert the Dictionary Config (from roles.json) into a List for the Frontend
        # Structure in JSON: "super_admin": { "legacy_id": 1, "db_name": "SuperAdmin", ... }
        for slug, details in _ROLES_DATA.items():
            role_obj = {
                "id": details.get("legacy_id"),
                "name": details.get("db_name"),
                "description": "Configured via roles.json" # Or add description to json later
            }
            roles_list.append(role_obj)
        
        # Sort by ID to ensure consistent dropdown order (1, 2, 3...)
        roles_list.sort(key=lambda x: x["id"])

        # Log the output
        logger.debug(f"CONFIG FETCH: Loaded {len(roles_list)} roles from config.\nDATA:\n{json.dumps(roles_list, indent=2)}")
        
        return roles_list

    except Exception as e:
        logger.critical(f"CONFIG ERROR in GET /roles: {e}", exc_info=True)
        # Fallback to hardcoded list if config crashes (Safety Net)
        return [
            {"id": 1, "name": "SuperAdmin", "description": "Fallback (Config Error)"},
            {"id": 2, "name": "Admin", "description": "Fallback (Config Error)"},
            {"id": 3, "name": "Site Manager", "description": "Fallback (Config Error)"}
        ]