"""Service layer for payslip calculations and exports."""

import logging
import traceback
from typing import Dict, List, Optional

from beanie.operators import RegEx

from backend.models import Attendance, CompanySettings, Deduction, Employee, Overtime
from backend.services.base_service import BaseService
from backend.utils.pdf_generator import generate_payslip_pdf

logger = logging.getLogger("MainApp")


class PayslipService(BaseService):
    """Payslip business logic with overtime and deduction aggregation."""

    async def calculate_single_payslip(self, employee_id: int, pay_period: str) -> Optional[Dict]:
        try:
            company_settings = await CompanySettings.find_one(CompanySettings.uid == 1)
            if not company_settings:
                company_settings = CompanySettings(
                    uid=1,
                    normal_overtime_multiplier=1.25,
                    offday_overtime_multiplier=1.5,
                    standard_hours_per_day=8,
                )

            emp = await Employee.find_one(Employee.uid == employee_id)
            if not emp:
                logger.warning("Employee ID %s not found.", employee_id)
                return None

            pattern = f"^{pay_period}"
            standard_days = emp.standard_work_days if emp.standard_work_days > 0 else 26
            full_basic_salary = 0.0
            leave_deduction_amount = 0.0
            days_absent = 0
            hourly_rate = 0.0

            attendance_docs = await Attendance.find(
                Attendance.employee_uid == employee_id,
                Attendance.status == "Present",
                RegEx(Attendance.date, pattern),
            ).to_list()
            days_present = len(attendance_docs)

            if emp.basic_salary > 0:
                full_basic_salary = emp.basic_salary
                daily_rate = full_basic_salary / standard_days
                hourly_rate = daily_rate / company_settings.standard_hours_per_day
                days_absent = max(0, standard_days - days_present)
                leave_deduction_amount = days_absent * daily_rate
            else:
                hourly_rate = emp.default_hourly_rate
                full_basic_salary = days_present * company_settings.standard_hours_per_day * hourly_rate

            total_overtime_salary = 0.0
            total_ot_hours = 0.0
            attendance_ot_hours = sum(getattr(doc, "overtime_hours", 0) for doc in attendance_docs)
            total_ot_hours += attendance_ot_hours
            total_overtime_salary += attendance_ot_hours * hourly_rate * company_settings.normal_overtime_multiplier

            explicit_overtime_docs = await Overtime.find(
                Overtime.employee_uid == employee_id,
                RegEx(Overtime.date, pattern),
            ).to_list()
            for ot in explicit_overtime_docs:
                multiplier = (
                    company_settings.offday_overtime_multiplier
                    if getattr(ot, "type", "Normal") == "Offday"
                    else company_settings.normal_overtime_multiplier
                )
                cost = ot.hours * hourly_rate * multiplier
                total_ot_hours += ot.hours
                total_overtime_salary += cost

            manual_deductions_list = await Deduction.find(
                Deduction.employee_uid == employee_id,
                Deduction.pay_period == pay_period,
            ).to_list()
            total_manual_deductions = sum(d.amount for d in manual_deductions_list)

            gross_earnings = full_basic_salary + total_overtime_salary + emp.allowance
            total_deductions = leave_deduction_amount + total_manual_deductions
            net_salary = gross_earnings - total_deductions

            return {
                "employee_id": emp.uid,
                "name": emp.name,
                "designation": emp.designation,
                "standard_work_days": standard_days,
                "pay_period": pay_period,
                "days_present": days_present,
                "days_absent": days_absent,
                "basic_salary_contract": round(full_basic_salary, 2),
                "leave_deduction_amount": round(leave_deduction_amount, 2),
                "overtime_hours": round(total_ot_hours, 2),
                "overtime_salary": round(total_overtime_salary, 2),
                "manual_deduction_amount": round(total_manual_deductions, 2),
                "allowance": round(emp.allowance, 2),
                "gross_salary": round(gross_earnings, 2),
                "total_deductions": round(total_deductions, 2),
                "net_salary": round(net_salary, 2),
            }
        except Exception:
            traceback.print_exc()
            return None

    async def calculate_payslips_preview(self, employee_ids: List[int], pay_period: str) -> List[Dict]:
        processed_payslips = []
        for emp_id in employee_ids:
            data = await self.calculate_single_payslip(emp_id, pay_period)
            if data:
                processed_payslips.append(data)
        return processed_payslips

    async def generate_payslip_pdf(self, employee_id: int, month: str):
        payslip_data = await self.calculate_single_payslip(employee_id, month)
        if not payslip_data:
            self.raise_not_found("Employee not found or calculation failed")
        return payslip_data, generate_payslip_pdf(payslip_data)
