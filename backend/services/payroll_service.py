"""Unified payroll service – works with ANY contract type (Phase 5B)."""

import logging
from typing import Any, Dict, List, Optional

from backend.models.salary_config import SalaryConfig
from backend.services.salary.configurable_calculator import ConfigurableSalaryCalculator
from backend.services.salary.fixed_calculator import FixedSalaryCalculator
from backend.services.salary.role_based_calculator import RoleBasedCalculator

logger = logging.getLogger("MainApp")


class PayrollService:
    """Universal payroll service that works with ANY contract type."""

    CALCULATORS = {
        "fixed": FixedSalaryCalculator(),
        "role_based": RoleBasedCalculator(),
        "configurable": ConfigurableSalaryCalculator(),
    }

    async def calculate_employee_salary(
        self,
        employee_id: int,
        contract_id: int,
        month: int,
        year: int,
        salary_config: Optional[SalaryConfig] = None,
    ) -> Dict[str, Any]:
        """Calculate salary for a single employee (works for ANY contract type)."""
        from backend.models import Contract

        contract = await Contract.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        calculator_type = getattr(contract, "salary_strategy", None) or "configurable"
        calculator = self.CALCULATORS.get(calculator_type)

        if not calculator:
            logger.warning(
                "Unknown salary strategy '%s'; falling back to 'configurable'.",
                calculator_type,
            )
            calculator = self.CALCULATORS["configurable"]

        return await calculator.calculate_monthly_salary(
            employee_id=employee_id,
            contract_id=contract_id,
            month=month,
            year=year,
            config=salary_config,
        )

    async def calculate_monthly_payroll(
        self,
        contract_id: int,
        month: int,
        year: int,
        salary_config: Optional[SalaryConfig] = None,
    ) -> Dict[str, Any]:
        """Calculate payroll for ALL employees in a contract for the given month."""
        from backend.models import Contract, LabourContract, RoleBasedContract

        contract = await Contract.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        # Determine which employee IDs belong to this contract
        employee_ids: List[int] = []

        if isinstance(contract, LabourContract):
            employee_ids = list(contract.assigned_employee_ids or [])
        elif isinstance(contract, RoleBasedContract):
            # For role-based contracts gather unique employee IDs from
            # DailyRoleFulfillment records for the target month.
            from calendar import monthrange
            from datetime import datetime

            from backend.models.role_contracts import DailyRoleFulfillment

            _, last_day = monthrange(year, month)
            start = datetime(year, month, 1)
            end = datetime(year, month, last_day, 23, 59, 59)

            fulfillments = await DailyRoleFulfillment.find(
                DailyRoleFulfillment.contract_id == contract_id,
                DailyRoleFulfillment.date >= start,
                DailyRoleFulfillment.date <= end,
            ).to_list()

            seen: set = set()
            for record in fulfillments:
                for slot in getattr(record, "filled_slots", []):
                    emp_id = getattr(slot, "employee_id", None)
                    if emp_id is not None and emp_id not in seen:
                        seen.add(emp_id)
                        employee_ids.append(emp_id)
        else:
            # Fallback: check for assigned_employee_ids attribute
            employee_ids = list(getattr(contract, "assigned_employee_ids", []))

        # Calculate salary for each employee
        payroll_results: List[Dict[str, Any]] = []
        total_payroll = 0.0

        for emp_id in employee_ids:
            salary_result = await self.calculate_employee_salary(
                employee_id=emp_id,
                contract_id=contract_id,
                month=month,
                year=year,
                salary_config=salary_config,
            )
            payroll_results.append(salary_result)
            total_payroll += salary_result.get("total", 0.0)

        return {
            "contract_id": contract_id,
            "contract_name": getattr(contract, "contract_name", None),
            "month": month,
            "year": year,
            "total_employees": len(employee_ids),
            "total_payroll": total_payroll,
            "employee_salaries": payroll_results,
        }
