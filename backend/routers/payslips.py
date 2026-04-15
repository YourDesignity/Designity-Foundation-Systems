import logging
import json
import traceback
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from beanie.operators import RegEx

# --- Imports ---
from backend.models import Employee, Attendance, Overtime, Deduction, CompanySettings
from backend.security import get_current_active_user
from backend.utils.pdf_generator import generate_payslip_pdf 
from backend.utils.logger import setup_logger 

router = APIRouter(
    prefix="/payslips",
    tags=["Payslips"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("PayslipsRouter", log_file="logs/payslips_router.log", level=logging.DEBUG)

class PayslipRequest(BaseModel):
    employee_ids: List[int]
    pay_period: str

# =============================================================================
# CORE LOGIC: CALCULATE SINGLE PAYSLIP
# =============================================================================

async def calculate_single_payslip(employee_id: int, pay_period: str) -> Optional[Dict]:
    """
    Calculates salary components including:
    1. Basic Salary (pro-rated by attendance).
    2. Overtime (Combining 'Attendance.overtime_hours' AND 'Overtime' collection).
    3. Manual Deductions.
    """
    try:
        # Load company settings
        company_settings = await CompanySettings.find_one(CompanySettings.uid == 1)
        if not company_settings:
            # Fallback to defaults if settings not found
            company_settings = CompanySettings(
                uid=1,
                normal_overtime_multiplier=1.25,
                offday_overtime_multiplier=1.5,
                standard_hours_per_day=8
            )

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            logger.warning(f"Employee ID {employee_id} not found.")
            return None

        # --- 1. SETUP & CONSTANTS ---
        pattern = f"^{pay_period}"
        standard_days = emp.standard_work_days if emp.standard_work_days > 0 else 26
        
        # Initialize Financials
        full_basic_salary = 0.0  
        earned_basic_salary = 0.0 
        leave_deduction_amount = 0.0
        days_absent = 0
        hourly_rate = 0.0

        # --- 2. ATTENDANCE FETCH ---
        # Fetch actual objects to access 'overtime_hours' field
        attendance_docs = await Attendance.find(
            Attendance.employee_uid == employee_id,
            Attendance.status == "Present",
            RegEx(Attendance.date, pattern)
        ).to_list()

        days_present = len(attendance_docs)

        # --- 3. BASIC SALARY CALCULATION ---
        if emp.basic_salary > 0:
            # -- Salaried Employee --
            full_basic_salary = emp.basic_salary
            daily_rate = full_basic_salary / standard_days
            hourly_rate = daily_rate / company_settings.standard_hours_per_day
            
            # Calculate Absence Cost
            days_absent = max(0, standard_days - days_present)
            leave_deduction_amount = days_absent * daily_rate
            
            # For reporting purposes
            earned_basic_salary = full_basic_salary 
        else:
            # -- Hourly Employee --
            hourly_rate = emp.default_hourly_rate
            earned_basic_salary = days_present * company_settings.standard_hours_per_day * hourly_rate
            full_basic_salary = earned_basic_salary 
            leave_deduction_amount = 0.0 

        # --- 4. OVERTIME CALCULATION (AGGREGATED) ---
        total_overtime_salary = 0.0
        total_ot_hours = 0.0

        # Source A: Daily Attendance Overtime (from 'overtime_hours' field)
        # We assume standard overtime rate (1.25x) for daily extensions
        attendance_ot_hours = sum(getattr(doc, "overtime_hours", 0) for doc in attendance_docs)
        total_ot_hours += attendance_ot_hours
        total_overtime_salary += (attendance_ot_hours * hourly_rate * company_settings.normal_overtime_multiplier)

        # Source B: Explicit Overtime Records (from Overtime Page)
        explicit_overtime_docs = await Overtime.find(
            Overtime.employee_uid == employee_id,
            RegEx(Overtime.date, pattern)
        ).to_list()

        for ot in explicit_overtime_docs:
            # Multiplier logic: Offday = 1.5, Normal = 1.25
            multiplier = company_settings.offday_overtime_multiplier if getattr(ot, 'type', 'Normal') == 'Offday' else company_settings.normal_overtime_multiplier
            cost = ot.hours * hourly_rate * multiplier
            
            total_ot_hours += ot.hours
            total_overtime_salary += cost

        logger.debug(f"OT CALC [Emp {employee_id}]: DailyHrs={attendance_ot_hours} | ExtraRecs={len(explicit_overtime_docs)} | TotalHrs={total_ot_hours}")

        # --- 5. MANUAL DEDUCTIONS ---
        manual_deductions_list = await Deduction.find(
            Deduction.employee_uid == employee_id,
            Deduction.pay_period == pay_period
        ).to_list()
        
        total_manual_deductions = sum(d.amount for d in manual_deductions_list)

        # --- 6. FINAL AGGREGATION ---
        gross_earnings = full_basic_salary + total_overtime_salary + emp.allowance
        total_deductions = leave_deduction_amount + total_manual_deductions
        net_salary = gross_earnings - total_deductions

        result_data = {
            "employee_id": emp.uid,
            "name": emp.name,
            "designation": emp.designation,
            "standard_work_days": standard_days,
            "pay_period": pay_period,
            "days_present": days_present,
            "days_absent": days_absent, 
            
            # Financial Breakdown
            "basic_salary_contract": round(full_basic_salary, 2),
            "leave_deduction_amount": round(leave_deduction_amount, 2),
            
            # Overtime Data (New fields for PDF)
            "overtime_hours": round(total_ot_hours, 2), 
            "overtime_salary": round(total_overtime_salary, 2),
            
            "manual_deduction_amount": round(total_manual_deductions, 2),
            "allowance": round(emp.allowance, 2),
            
            # Totals
            "gross_salary": round(gross_earnings, 2),
            "total_deductions": round(total_deductions, 2),
            "net_salary": round(net_salary, 2)
        }
        
        return result_data

    except Exception as e:
        logger.error(f"CALC ERROR for Emp {employee_id}: {e}")
        traceback.print_exc()
        return None

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/calculate")
async def calculate_payslips_preview(request: PayslipRequest):
    logger.info(f"ENDPOINT START: POST /payslips/calculate. Batch Size: {len(request.employee_ids)}")
    processed_payslips = []
    try:
        for emp_id in request.employee_ids:
            data = await calculate_single_payslip(emp_id, request.pay_period)
            if data:
                processed_payslips.append(data)
                
        return {
            "status": "success",
            "message": f"Calculated {len(processed_payslips)} payslips.",
            "payslips_data": processed_payslips
        }
    except Exception as e:
        logger.critical(f"BATCH CALCULATION CRASH: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{employee_id}")
async def download_payslip_pdf(employee_id: int, month: str):
    try:
        # 1. Calculate Data
        payslip_data = await calculate_single_payslip(employee_id, month)
        if not payslip_data:
            raise HTTPException(status_code=404, detail="Employee not found or calculation failed")
        
        # 2. Generate PDF
        pdf_buffer = generate_payslip_pdf(payslip_data)
        
        # 3. Serve File
        filename = f"Payslip_{payslip_data['name']}_{payslip_data['pay_period']}.pdf"
        
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.critical(f"PDF ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"PDF Generation Failed: {str(e)}")