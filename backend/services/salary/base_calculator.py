"""Abstract base class for salary calculation strategies (Phase 5B)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from backend.models.salary_config import SalaryConfig


class SalaryCalculator(ABC):
    """Base interface for salary calculation strategies."""

    @abstractmethod
    async def calculate_monthly_salary(
        self,
        employee_id: int,
        contract_id: int,
        month: int,
        year: int,
        config: Optional[SalaryConfig] = None,
    ) -> Dict[str, Any]:
        """
        Calculate monthly salary for an employee.

        Returns a dict with structure::

            {
                "employee_id": int,
                "employee_name": str,
                "base_salary": float,
                "allowances": Dict[str, float],
                "bonuses": Dict[str, float],
                "deductions": Dict[str, float],
                "overtime": float,
                "period_modifiers": Dict[str, float],
                "total": float,
                "breakdown": Dict[str, Any],
            }
        """
