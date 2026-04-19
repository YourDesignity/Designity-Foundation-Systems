"""Global module settings model."""

from datetime import datetime
from typing import Dict, Optional

from beanie import Document
from pydantic import Field


class GlobalModuleSettings(Document):
    """
    Global module configuration for the application.
    Only one document should exist (singleton pattern, uid=1).
    """

    uid: int = Field(default=1)  # Singleton document

    modules_enabled: Dict[str, bool] = Field(
        default_factory=lambda: {
            "employee": True,
            "inventory": True,
            "vehicle": True,
        }
    )

    default_configs: Dict[str, Dict] = Field(
        default_factory=lambda: {
            "employee": {
                "max_employees": 50,
                "require_role_assignment": True,
                "track_attendance": True,
                "allow_overtime": False,
                "salary_calculation": "monthly",
            },
            "inventory": {
                "track_movements": True,
                "require_return_date": True,
                "alert_low_stock": True,
                "auto_deduct": False,
            },
            "vehicle": {
                "track_mileage": True,
                "require_driver_assignment": True,
                "maintenance_alerts": True,
                "fuel_tracking": False,
            },
        }
    )

    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_admin_id: Optional[int] = None
    updated_by_admin_name: Optional[str] = None

    class Settings:
        name = "global_module_settings"
