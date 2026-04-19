"""Service layer for company settings management."""

import logging
from datetime import datetime
from typing import Any

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class SettingsService(BaseService):
    """Business logic for company settings."""

    async def get_company_settings(self):
        from backend.models import CompanySettings

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)

        if not settings:
            settings = CompanySettings(
                uid=1,
                normal_overtime_multiplier=1.25,
                offday_overtime_multiplier=1.5,
                standard_hours_per_day=8,
                enable_absence_deduction=True,
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
            "updated_by": settings.updated_by_admin_name,
        }

    async def update_company_settings(self, request: Any, current_user: dict):
        from backend.models import CompanySettings

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only SuperAdmin and Admin can modify company settings")

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)

        if not settings:
            settings = CompanySettings(uid=1)

        update_data = request.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(settings, key, value)

        settings.updated_at = datetime.now()
        settings.updated_by_admin_id = current_user.get("id")
        settings.updated_by_admin_name = current_user.get("name", "Admin")

        await settings.save()

        logger.info("Settings updated by %s (ID: %s)", current_user.get("name"), current_user.get("id"))

        return {"message": "Company settings updated successfully"}
