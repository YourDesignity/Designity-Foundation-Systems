# backend/routers/modules.py

import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models.module_settings import GlobalModuleSettings
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/api/modules",
    tags=["Module Settings"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("ModulesRouter", log_file="logs/modules_router.log", level=logging.DEBUG)

# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class ModuleSettingsUpdate(BaseModel):
    modules_enabled: Optional[Dict[str, bool]] = None
    default_configs: Optional[Dict[str, Dict]] = None


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/settings")
async def get_global_module_settings(current_user: dict = Depends(get_current_active_user)):
    """
    Get global module settings. Returns defaults if no settings have been saved yet.
    All authenticated roles can view settings.
    """
    settings = await GlobalModuleSettings.find_one(GlobalModuleSettings.uid == 1)
    if not settings:
        # Return default settings without persisting
        settings = GlobalModuleSettings()
        logger.debug("No global module settings found; returning defaults.")
    return settings


@router.put("/settings")
async def update_global_module_settings(
    payload: ModuleSettingsUpdate,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Update global module settings. SuperAdmin and Admin only.
    Creates the singleton document on first save.
    """
    role = current_user.get("role", "")
    if role not in ("SuperAdmin", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin or Admin can update module settings.",
        )

    settings = await GlobalModuleSettings.find_one(GlobalModuleSettings.uid == 1)
    if not settings:
        settings = GlobalModuleSettings(uid=1)

    if payload.modules_enabled is not None:
        settings.modules_enabled = payload.modules_enabled

    if payload.default_configs is not None:
        settings.default_configs = payload.default_configs

    settings.updated_at = datetime.now()
    settings.updated_by_admin_id = current_user.get("id")
    settings.updated_by_admin_name = current_user.get("full_name")

    await settings.save()

    logger.info(
        f"Module settings updated by {current_user.get('sub')} "
        f"(ID: {current_user.get('id')})"
    )
    return settings
