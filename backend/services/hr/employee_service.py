"""Service layer for employee operations."""

from typing import Any, List

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class EmployeeService(BaseService):
    """Employee-related business operations."""

    async def create_employee(self, payload: Any):
        from backend.models import Employee

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("employees")
        employee = Employee(**data)
        await employee.insert()
        return employee

    async def get_employee_by_id(self, employee_id: int):
        from backend.models import Employee

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found(f"Employee {employee_id} not found")
        return employee

    async def get_employee_if_exists(self, employee_id: int):
        from backend.models import Employee

        return await Employee.find_one(Employee.uid == employee_id)

    async def get_employees(self):
        from backend.models import Employee

        return await Employee.find_all().sort("+uid").to_list()

    async def update_employee(self, employee_id: int, payload: Any):
        employee = await self.get_employee_by_id(employee_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(employee, field, value)
        await employee.save()
        return employee

    async def delete_employee(self, employee_id: int) -> bool:
        employee = await self.get_employee_by_id(employee_id)
        await employee.delete()
        return True

    async def validate_designation(self, employee_id: int, expected_designation: str, detail_prefix: str):
        employee = await self.get_employee_if_exists(employee_id)
        if employee and employee.designation != expected_designation:
            self.raise_bad_request(
                f"{detail_prefix} designation '{employee.designation}' does not match slot designation '{expected_designation}'"
            )
        return employee

    async def get_available_employees_by_designation(self, designation: str) -> List[Any]:
        from backend.models import Employee

        return await Employee.find(
            Employee.designation == designation,
            Employee.status == "Active",
            Employee.availability_status == "Available",
        ).to_list()
