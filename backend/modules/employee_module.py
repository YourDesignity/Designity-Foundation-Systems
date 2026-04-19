"""Employee management module for contracts."""

from datetime import date, datetime
from typing import Any, Dict, List

from backend.modules.base_module import ContractModule


class EmployeeModule(ContractModule):
    """
    Module for managing fixed employee assignments to contracts.
    Handles employee costs, attendance, and assignment validation.
    """

    module_name = "employee"
    required_models = ["Employee", "EmployeeAssignment"]

    async def initialize(self, contract: Any) -> Dict[str, Any]:
        """Initialize employee module for contract."""
        from backend.models.assignments import EmployeeAssignment

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.contract_id == contract.uid
        ).to_list()

        return {
            "module": self.module_name,
            "status": "initialized",
            "assigned_employees": len(assignments),
            "employee_ids": [a.employee_id for a in assignments],
        }

    async def calculate_cost(
        self,
        contract: Any,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Calculate total employee costs for this contract for the given month.

        Cost = Sum of (employee.basic_salary + employee.allowance) for all assigned employees.
        """
        from backend.models.assignments import EmployeeAssignment
        from backend.models.hr import Employee

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.contract_id == contract.uid
        ).to_list()

        if not assignments:
            return {
                "module": self.module_name,
                "total_cost": 0.0,
                "employee_count": 0,
                "breakdown_by_designation": {},
                "employees": [],
            }

        employee_ids = [a.employee_id for a in assignments]
        employees = await Employee.find(
            Employee.uid.in_(employee_ids)
        ).to_list()

        total_cost = 0.0
        breakdown_by_designation: Dict[str, Dict[str, Any]] = {}
        employee_details: List[Dict[str, Any]] = []

        for emp in employees:
            emp_cost = (emp.basic_salary or 0.0) + (emp.allowance or 0.0)
            total_cost += emp_cost

            designation = emp.designation
            if designation not in breakdown_by_designation:
                breakdown_by_designation[designation] = {
                    "count": 0,
                    "total_cost": 0.0,
                }
            breakdown_by_designation[designation]["count"] += 1
            breakdown_by_designation[designation]["total_cost"] += emp_cost

            employee_details.append(
                {
                    "employee_id": emp.uid,
                    "name": emp.name,
                    "designation": emp.designation,
                    "monthly_cost": emp_cost,
                }
            )

        return {
            "module": self.module_name,
            "total_cost": total_cost,
            "employee_count": len(employees),
            "breakdown_by_designation": breakdown_by_designation,
            "employees": employee_details,
        }

    async def validate(
        self,
        contract: Any,
        date: Any,
    ) -> Dict[str, Any]:
        """
        Validate that all assigned employees are present/available on the given date.
        """
        from backend.models.assignments import EmployeeAssignment
        from backend.models.hr import Attendance

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.contract_id == contract.uid
        ).to_list()

        if not assignments:
            return {
                "module": self.module_name,
                "is_valid": True,
                "message": "No employees assigned",
                "issues": [],
                "warnings": [],
            }

        employee_ids = [a.employee_id for a in assignments]

        # Normalise to date string (Attendance.date is stored as str "YYYY-MM-DD")
        if isinstance(date, datetime):
            target_date = date.date()
        elif isinstance(date, str):
            target_date = datetime.fromisoformat(date).date()
        else:
            target_date = date  # already a datetime.date

        target_str = target_date.isoformat()

        attendance_records = await Attendance.find(
            Attendance.employee_uid.in_(employee_ids),
            Attendance.date == target_str,
        ).to_list()

        present: List[int] = []
        absent: List[int] = []
        no_record: List[int] = []

        for emp_id in employee_ids:
            att = next(
                (a for a in attendance_records if a.employee_uid == emp_id), None
            )
            if att:
                if att.status == "Present":
                    present.append(emp_id)
                else:
                    absent.append(emp_id)
            else:
                no_record.append(emp_id)

        issues = []
        warnings = []

        if absent:
            issues.append(f"{len(absent)} employees absent on {target_str}")

        if no_record:
            warnings.append(
                f"{len(no_record)} employees have no attendance record"
            )

        return {
            "module": self.module_name,
            "is_valid": len(issues) == 0,
            "date": target_str,
            "total_assigned": len(employee_ids),
            "present_count": len(present),
            "absent_count": len(absent),
            "no_record_count": len(no_record),
            "issues": issues,
            "warnings": warnings,
        }

    async def get_resource_requirements(self, contract: Any) -> Dict[str, Any]:
        """Get employee requirements for this contract."""
        from backend.models.assignments import EmployeeAssignment
        from backend.models.hr import Employee

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.contract_id == contract.uid
        ).to_list()

        employee_ids = [a.employee_id for a in assignments]
        employees = await Employee.find(
            Employee.uid.in_(employee_ids)
        ).to_list()

        by_designation: Dict[str, List[Dict[str, Any]]] = {}
        for emp in employees:
            if emp.designation not in by_designation:
                by_designation[emp.designation] = []
            by_designation[emp.designation].append(
                {"id": emp.uid, "name": emp.name}
            )

        return {
            "module": self.module_name,
            "total_employees": len(employees),
            "by_designation": by_designation,
        }
