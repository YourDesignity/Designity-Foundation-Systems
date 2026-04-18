"""Payroll API endpoints (Phase 5B)."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.models.salary_config import SalaryConfig
from backend.security import get_current_active_user
from backend.services.payroll_service import PayrollService

logger = logging.getLogger("MainApp")

router = APIRouter(
    prefix="/payroll",
    tags=["Payroll"],
    dependencies=[Depends(get_current_active_user)],
)

payroll_service = PayrollService()


class CalculateSalaryRequest(BaseModel):
    employee_id: int
    contract_id: int
    month: int
    year: int
    salary_config: Optional[SalaryConfig] = None


@router.post("/calculate-salary")
async def calculate_employee_salary(request: CalculateSalaryRequest):
    """Calculate salary for a single employee with an optional custom config."""
    try:
        return await payroll_service.calculate_employee_salary(
            employee_id=request.employee_id,
            contract_id=request.contract_id,
            month=request.month,
            year=request.year,
            salary_config=request.salary_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Payroll calculation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/contract/{contract_id}/month/{month}/year/{year}")
async def calculate_contract_payroll(contract_id: int, month: int, year: int):
    """Calculate total payroll for a contract for a specific month."""
    try:
        return await payroll_service.calculate_monthly_payroll(
            contract_id=contract_id,
            month=month,
            year=year,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Monthly payroll calculation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
