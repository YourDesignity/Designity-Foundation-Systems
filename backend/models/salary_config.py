"""Pydantic models for configurable salary calculation (Phase 5B)."""

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class OvertimeRule(BaseModel):
    """Overtime calculation rules."""

    enabled: bool = True
    threshold_hours_per_day: float = 8.0
    multiplier: float = 1.5
    max_hours_per_month: Optional[float] = None


class PeriodModifier(BaseModel):
    """Special period bonuses (Ramadan, holidays, etc.)."""

    name: str  # "ramadan", "eid", "national_day"
    start_date: date
    end_date: date
    modifier_type: str  # "percentage" | "fixed_amount"
    value: float  # 20.0 for 20% or 500.0 for flat bonus
    applies_to: List[str] = Field(default_factory=lambda: ["base_salary", "allowances"])


class DeductionRule(BaseModel):
    """Deduction rules (late arrival, absence, etc.)."""

    name: str
    deduction_type: str  # "percentage" | "fixed_amount" | "per_occurrence"
    value: float
    condition: str  # "late_arrival" | "absence" | "half_day"
    max_deduction_per_month: Optional[float] = None


class BonusRule(BaseModel):
    """Bonus rules (performance, perfect attendance, etc.)."""

    name: str
    bonus_type: str  # "percentage" | "fixed_amount"
    value: float
    condition: str  # "perfect_attendance" | "performance_rating"
    min_qualifying_value: Optional[float] = None


class SalaryConfig(BaseModel):
    """Complete salary configuration."""

    # Base rules
    attendance_required: bool = True
    pro_rate_on_absence: bool = True

    # Overtime
    overtime: OvertimeRule = Field(default_factory=OvertimeRule)

    # Period modifiers (Ramadan, holidays)
    period_modifiers: List[PeriodModifier] = []

    # Deductions
    deductions: List[DeductionRule] = []

    # Bonuses
    bonuses: List[BonusRule] = []

    # Allowances
    allowances: Dict[str, float] = {}  # {"transport": 100, "food": 50}
