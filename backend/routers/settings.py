import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.models import CompanySettings
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("SettingsRouter", log_file="logs/settings.log", level=logging.DEBUG)

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
    settings = await CompanySettings.find_one(CompanySettings.uid == 1)

    if not settings:
        # Create default settings if none exist
        settings = CompanySettings(
            uid=1,
            normal_overtime_multiplier=1.25,
            offday_overtime_multiplier=1.5,
            standard_hours_per_day=8,
            enable_absence_deduction=True
        )
        await settings.insert()
        logger.info("Created default company settings")

    return {
        "normal_overtime_multiplier": settings.normal_overtime_multiplier,
        "offday_overtime_multiplier": settings.offday_overtime_multiplier,
        "standard_hours_per_day": settings.standard_hours_per_day,
        "enable_absence_deduction": settings.enable_absence_deduction,
        "custom_storage_path": settings.custom_storage_path,
        "enable_local_storage": settings.enable_local_storage,
        "use_employee_name_in_filename": settings.use_employee_name_in_filename,
        "last_updated": settings.updated_at.isoformat() if settings.updated_at else None,
        "updated_by": settings.updated_by_admin_name
    }


@router.put("/")
async def update_company_settings(
    request: UpdateSettingsRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update company settings. SuperAdmin/Admin only.
    """
    # Permission check
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only SuperAdmin and Admin can modify company settings"
        )

    settings = await CompanySettings.find_one(CompanySettings.uid == 1)

    if not settings:
        # Create if doesn't exist
        settings = CompanySettings(uid=1)

    # Apply updates
    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)

    # Update metadata
    settings.updated_at = datetime.now()
    settings.updated_by_admin_id = current_user.get("id")
    settings.updated_by_admin_name = current_user.get("name", "Admin")

    await settings.save()

    logger.info(f"Settings updated by {current_user.get('name')} (ID: {current_user.get('id')})")

    return {"message": "Company settings updated successfully"}
