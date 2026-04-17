import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.settings_service import SettingsService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("SettingsRouter", log_file="logs/settings.log", level=logging.DEBUG)
service = SettingsService()

# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class UpdateSettingsRequest(BaseModel):
    normal_overtime_multiplier: Optional[float] = None
    offday_overtime_multiplier: Optional[float] = None
    standard_hours_per_day: Optional[int] = None
    enable_absence_deduction: Optional[bool] = None
    custom_storage_path: Optional[str] = None
    enable_local_storage: Optional[bool] = None
    use_employee_name_in_filename: Optional[bool] = None

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/")
async def get_company_settings(current_user: dict = Depends(get_current_active_user)):
    """
    Get company settings. All roles can view settings.
    """
    return await service.get_company_settings()


@router.put("/")
async def update_company_settings(
    request: UpdateSettingsRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update company settings. SuperAdmin/Admin only.
    """
    return await service.update_company_settings(request, current_user)
