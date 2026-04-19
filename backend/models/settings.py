"""Application/company-level settings models."""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class CompanySettings(Document):
    """
    Company-wide configuration for salary calculations and business rules.
    Only one settings document should exist (singleton pattern).
    """

    uid: int = 1  # Always 1 (singleton)

    # Overtime Multipliers
    normal_overtime_multiplier: float = 1.25  # Normal OT rate (default: 25% premium)
    offday_overtime_multiplier: float = 1.5  # Off-day OT rate (default: 50% premium)

    # Work Hours
    standard_hours_per_day: int = 8  # Default work hours per day

    # Absence Penalties
    enable_absence_deduction: bool = True  # Whether to deduct for absences

    # File Storage Configuration
    custom_storage_path: Optional[str] = None  # e.g., "D:\\MONTREAL_Files"
    enable_local_storage: bool = True  # Enable/disable custom folder backup
    use_employee_name_in_filename: bool = True  # Use "13_Naveen.jpg" vs "emp_13_20260404.jpg"

    # Metadata
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_admin_id: Optional[int] = None
    updated_by_admin_name: Optional[str] = None

    # ===== PROJECT WORKFLOW SETTINGS (NEW) =====
    auto_generate_project_codes: bool = True  # Auto-generate PRJ-001, PRJ-002, etc.
    auto_generate_contract_codes: bool = True  # Auto-generate CNT-001, CNT-002, etc.
    auto_generate_site_codes: bool = True  # Auto-generate SITE-001, SITE-002, etc.

    project_code_prefix: str = "PRJ"
    contract_code_prefix: str = "CNT"
    site_code_prefix: str = "SITE"

    # Contract expiry alerts
    contract_expiry_warning_days: int = 30  # Alert when contract expires in X days

    # External worker settings
    default_external_worker_daily_rate: float = 15.0  # Default daily rate in KD
    default_external_worker_hourly_rate: float = 1.875  # Default hourly rate in KD

    class Settings:
        name = "company_settings"
