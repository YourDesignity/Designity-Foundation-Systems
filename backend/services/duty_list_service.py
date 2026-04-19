"""Service layer for duty list management."""

import logging
from typing import Any, List

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class DutyListService(BaseService):
    """Business logic for duty assignment CRUD."""

    async def create_duty_assignments(self, assignments: List[Any], current_user: dict) -> dict:
        from backend.models import DutyAssignment, Employee

        if current_user.get("role") not in ["SuperAdmin", "Admin", "Site Manager"]:
            self.raise_forbidden("Only Admins and Site Managers can assign workforce duties.")

        for item in assignments:
            payload = item.model_dump() if hasattr(item, "model_dump") else dict(item)

            employee_id = payload.get("employee_id")
            manager_id = payload.get("manager_id")
            site_id = payload.get("site_id")
            start_date = payload.get("start_date")
            end_date = payload.get("end_date")

            employee = await Employee.find_one(Employee.uid == employee_id)
            if employee:
                employee.manager_id = manager_id
                await employee.save()
                logger.info("Updated employee manager mapping for duty assignment")

            existing = await DutyAssignment.find_one(
                DutyAssignment.employee_id == employee_id
            )

            if existing:
                existing.site_id = site_id
                existing.manager_id = manager_id
                existing.start_date = start_date
                existing.end_date = end_date
                await existing.save()
                logger.info("Updated existing duty assignment record")
            else:
                new_duty = DutyAssignment(
                    employee_id=employee_id,
                    site_id=site_id,
                    manager_id=manager_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                await new_duty.insert()
                logger.info("Created new duty assignment record")

        return {"message": "Duty assigned to employees successfully"}

    async def get_duty_list_by_date(self, date_str: str, current_user: dict):
        from backend.models import DutyAssignment, Admin

        user_role = current_user.get("role")
        user_email = current_user.get("sub")

        if user_role not in ["SuperAdmin", "Admin", "Site Manager"]:
            self.raise_forbidden("Only SuperAdmin, Admin, and Site Manager roles can access duty lists")

        me = await Admin.find_one(Admin.email == user_email)

        if user_role in ["SuperAdmin", "Admin"]:
            return await DutyAssignment.find(
                DutyAssignment.start_date <= date_str,
                DutyAssignment.end_date >= date_str,
            ).to_list()

        if not me:
            return []

        return await DutyAssignment.find(
            DutyAssignment.manager_id == me.uid,
            DutyAssignment.start_date <= date_str,
            DutyAssignment.end_date >= date_str,
        ).to_list()

    async def delete_duty_assignment(self, assignment_id: str):
        from backend.models import DutyAssignment

        record = await DutyAssignment.get(assignment_id)
        if not record:
            self.raise_not_found("Assignment not found")
        await record.delete()
        return {"message": "Assignment removed"}
