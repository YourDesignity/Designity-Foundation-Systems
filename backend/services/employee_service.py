from typing import List, Optional

from backend.models import Employee
from backend.services.base_service import BaseService


class EmployeeService(BaseService):
    """Employee-related business operations."""

    async def get_employee(self, employee_id: int) -> Optional[Employee]:
        return await Employee.find_one(Employee.uid == employee_id)

    async def ensure_employee(self, employee_id: int) -> Employee:
        employee = await self.get_employee(employee_id)
        if not employee:
            self.raise_not_found(f"Employee {employee_id} not found")
        return employee

    async def validate_designation(self, employee_id: int, expected_designation: str, detail_prefix: str) -> Optional[Employee]:
        employee = await self.get_employee(employee_id)
        if employee and employee.designation != expected_designation:
            self.raise_bad_request(
                f"{detail_prefix} designation '{employee.designation}' does not match slot designation '{expected_designation}'"
            )
        return employee

    async def get_available_employees_by_designation(self, designation: str) -> List[Employee]:
        return await Employee.find(
            Employee.designation == designation,
            Employee.status == "Active",
            Employee.availability_status == "Available",
        ).to_list()
