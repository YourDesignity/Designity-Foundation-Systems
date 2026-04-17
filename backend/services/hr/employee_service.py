"""Service layer for employee business operations."""

import logging
from datetime import date, datetime, timedelta
from typing import Any, List, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class EmployeeService(BaseService):
    """Employee lifecycle, search, and compliance operations."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _parse_date(value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        if isinstance(value, str):
            try:
                d = date.fromisoformat(value)
                return datetime(d.year, d.month, d.day)
            except ValueError:
                return None
        return None

    async def create_employee(self, payload: Any):
        """
        Create a new employee record.

        Validations:
        - Optional manager_id must reference a Site Manager
        - Date fields are normalized for BSON compatibility

        Args:
            payload: Employee create payload (dict or schema/model)

        Returns:
            Created Employee document

        Raises:
            HTTPException 400: Invalid manager reference
        """
        from backend.models import Admin, Employee

        data = self._to_dict(payload)
        manager_id = data.get("manager_id")
        if manager_id is not None:
            mgr = await Admin.find_one(Admin.uid == manager_id)
            if not mgr or mgr.role != "Site Manager":
                self.raise_bad_request("Invalid manager ID: must be an active Site Manager")

        new_uid = await self.get_next_uid("employees")
        employee = Employee(
            uid=new_uid,
            name=data.get("name", ""),
            designation=data.get("designation", ""),
            basic_salary=float(data.get("basic_salary", 0.0)),
            standard_work_days=int(data.get("standard_work_days", 28)),
            employee_type=data.get("employee_type", "Company"),
            allowance=float(data.get("allowance", 0.0)),
            default_hourly_rate=float(data.get("default_hourly_rate", 0.0)),
            status=data.get("status") or data.get("status_field", "Active"),
            nationality=data.get("nationality"),
            permanent_address=data.get("permanent_address"),
            phone_kuwait=data.get("phone_kuwait"),
            phone_home_country=data.get("phone_home_country"),
            emergency_contact_name=data.get("emergency_contact_name"),
            emergency_contact_number=data.get("emergency_contact_number"),
            civil_id_number=data.get("civil_id_number"),
            civil_id_expiry=self._parse_date(data.get("civil_id_expiry")),
            passport_number=data.get("passport_number"),
            passport_expiry=self._parse_date(data.get("passport_expiry")),
            date_of_joining=self._parse_date(data.get("date_of_joining")),
            contract_end_date=self._parse_date(data.get("contract_end_date")),
            date_of_birth=self._parse_date(data.get("date_of_birth")),
            passport_path=data.get("passport_path"),
            visa_path=data.get("visa_path"),
            manager_id=manager_id,
        )
        await employee.insert()
        logger.info("Employee created: %s (ID: %s)", employee.name, employee.uid)
        return employee

    async def update_employee(self, employee_id: int, payload: Any):
        """
        Update employee details.

        Validations:
        - Employee must exist
        - Optional manager_id must reference Site Manager

        Args:
            employee_id: Employee UID
            payload: Employee update payload

        Returns:
            Updated Employee document

        Raises:
            HTTPException 404: Employee not found
            HTTPException 400: Invalid manager reference
        """
        from backend.models import Admin, Employee

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")

        update_data = self._to_dict(payload)
        manager_id = update_data.get("manager_id")
        if manager_id is not None:
            mgr = await Admin.find_one(Admin.uid == manager_id)
            if not mgr or mgr.role != "Site Manager":
                self.raise_bad_request("Invalid manager ID: must be an active Site Manager")

        for key, value in update_data.items():
            if key in {
                "date_of_birth",
                "civil_id_expiry",
                "passport_expiry",
                "date_of_joining",
                "contract_end_date",
            }:
                setattr(employee, key, self._parse_date(value))
            else:
                setattr(employee, key, value)

        await employee.save()
        logger.info("Employee updated")
        return employee

    async def search_employees(
        self,
        query: Optional[str] = None,
        designation: Optional[str] = None,
        status: Optional[str] = None,
        manager_id: Optional[int] = None,
        employee_type: Optional[str] = None,
    ) -> List[Any]:
        """
        Search employees with optional filters.

        Validations:
        - All filters are optional and combined using AND semantics

        Args:
            query: Text query for name/civil_id/passport
            designation: Designation filter
            status: Employee status filter
            manager_id: Manager UID filter
            employee_type: Company/Outsourced filter

        Returns:
            Employee list sorted by UID
        """
        from backend.models import Employee

        filters = []
        if designation:
            filters.append(Employee.designation == designation)
        if status:
            filters.append(Employee.status == status)
        if manager_id is not None:
            filters.append(Employee.manager_id == manager_id)
        if employee_type:
            filters.append(Employee.employee_type == employee_type)

        if query:
            needle = query.strip().lower()
            candidates = await (Employee.find(*filters).sort("+uid").to_list() if filters else Employee.find_all().sort("+uid").to_list())
            return [
                emp
                for emp in candidates
                if needle in (emp.name or "").lower()
                or needle in (emp.designation or "").lower()
                or needle in (emp.civil_id_number or "").lower()
                or needle in (emp.passport_number or "").lower()
            ]

        return await (Employee.find(*filters).sort("+uid").to_list() if filters else Employee.find_all().sort("+uid").to_list())

    async def get_expiring_documents(self, within_days: int = 30) -> list[dict]:
        """
        Get employees whose Civil ID or Passport expires soon.

        Validations:
        - within_days must be non-negative

        Args:
            within_days: Non-negative days-ahead window
                        (0 returns documents expiring today)

        Returns:
            List of expiring document summary rows
        """
        from backend.models import Employee

        if within_days < 0:
            self.raise_bad_request("within_days must be non-negative")

        now = datetime.combine(date.today(), datetime.min.time())
        window_end = now + timedelta(days=within_days)
        employees = await Employee.find_all().to_list()

        rows: list[dict] = []
        for emp in employees:
            if emp.civil_id_expiry and now <= emp.civil_id_expiry <= window_end:
                rows.append(
                    {
                        "employee_id": emp.uid,
                        "employee_name": emp.name,
                        "document_type": "civil_id",
                        "expiry_date": emp.civil_id_expiry.date().isoformat(),
                        "days_remaining": (emp.civil_id_expiry - now).days,
                    }
                )
            if emp.passport_expiry and now <= emp.passport_expiry <= window_end:
                rows.append(
                    {
                        "employee_id": emp.uid,
                        "employee_name": emp.name,
                        "document_type": "passport",
                        "expiry_date": emp.passport_expiry.date().isoformat(),
                        "days_remaining": (emp.passport_expiry - now).days,
                    }
                )
        return sorted(rows, key=lambda item: item["days_remaining"])

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

    async def delete_employee(self, employee_id: int) -> bool:
        employee = await self.get_employee_by_id(employee_id)
        await employee.delete()
        logger.info("Employee deleted")
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
