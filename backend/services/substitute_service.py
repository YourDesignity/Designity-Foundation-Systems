"""Service layer for substitute management operations."""

import logging
from datetime import date, datetime
from typing import List, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class SubstituteService(BaseService):
    """Business logic for outsourced substitute employee management."""

    async def get_available_substitutes(self, site_id: Optional[int] = None) -> dict:
        """Get outsourced employees available as substitutes."""
        from backend.models import Employee

        substitutes = await Employee.find(
            Employee.employee_type == "Outsourced",
            Employee.status == "Active",
            Employee.can_be_substitute == True,  # noqa: E712
            Employee.substitute_availability == "available",
        ).to_list()

        result = [emp.model_dump(mode="json") for emp in substitutes]
        logger.info("Retrieved %d available substitutes", len(result))
        return {"total": len(result), "substitutes": result}

    async def get_all_outsourced_employees(self) -> dict:
        """Get all outsourced/external employees."""
        from backend.models import Employee

        employees = await Employee.find(
            Employee.employee_type == "Outsourced",
            Employee.status == "Active",
        ).to_list()

        return {
            "total": len(employees),
            "employees": [e.model_dump(mode="json") for e in employees],
        }

    async def assign_substitute(
        self,
        employee_id: int,
        site_id: int,
        start_date: date,
        end_date: Optional[date],
        reason: str,
        replacing_employee_id: Optional[int],
        daily_rate: Optional[float],
        hourly_rate: Optional[float],
        current_user: dict,
    ) -> dict:
        """Assign an outsourced employee as a substitute to a site."""
        from backend.models import (
            Admin, Employee, Site, SubstituteAssignment, TemporaryAssignment,
        )

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")
        if employee.employee_type != "Outsourced":
            self.raise_bad_request("Only Outsourced employees can be assigned as substitutes")
        if employee.current_substitute_assignment and employee.current_substitute_assignment.status == "Active":
            self.raise_bad_request("Employee is already on an active substitute assignment")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        manager_id = current_user.get("id")
        if current_user.get("role") == "Site Manager":
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if me:
                manager_id = me.uid

        replacing_name = None
        if replacing_employee_id:
            replacing_emp = await Employee.find_one(Employee.uid == replacing_employee_id)
            replacing_name = replacing_emp.name if replacing_emp else None

        assignment = SubstituteAssignment(
            site_id=site_id,
            site_name=site.name,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.min.time()) if end_date else None,
            reason=reason,
            replacing_employee_id=replacing_employee_id,
            replacing_employee_name=replacing_name,
            assigned_by_manager_id=manager_id,
            daily_rate=daily_rate or employee.default_hourly_rate,
            hourly_rate=hourly_rate,
            status="Active",
        )

        employee.current_substitute_assignment = assignment
        employee.substitute_availability = "assigned"
        employee.can_be_substitute = True
        employee.substitute_assignment_history.append(assignment)
        employee.total_substitute_assignments += 1
        await employee.save()

        if employee.uid not in site.active_substitute_uids:
            site.active_substitute_uids.append(employee.uid)
            await site.save()

        new_uid = await self.get_next_uid("temporary_assignments")
        temp_assignment = TemporaryAssignment(
            uid=new_uid,
            employee_id=employee_id,
            employee_name=employee.name,
            employee_type="Outsourced",
            employee_designation=employee.designation,
            assignment_type="Temporary",
            site_id=site_id,
            site_name=site.name,
            project_id=site.project_id or 0,
            manager_id=manager_id,
            replacing_employee_id=replacing_employee_id,
            replacing_employee_name=replacing_name,
            replacement_reason=reason,
            start_date=start_date,
            end_date=end_date or start_date,
            total_days=(end_date - start_date).days + 1 if end_date else 1,
            rate_type="Daily" if daily_rate else "Hourly",
            daily_rate=daily_rate or 0.0,
            hourly_rate=hourly_rate or 0.0,
            status="Active",
            created_by_admin_id=current_user.get("id"),
        )
        await temp_assignment.insert()

        logger.info("Substitute %s assigned to site %s for reason: %s", employee.name, site.name, reason)

        return {
            "message": "Substitute assigned successfully",
            "employee_id": employee_id,
            "employee_name": employee.name,
            "site_id": site_id,
            "site_name": site.name,
            "reason": reason,
            "temporary_assignment_id": temp_assignment.uid,
        }

    async def release_substitute(
        self,
        employee_id: int,
        end_date: Optional[date],
    ) -> dict:
        """Release a substitute employee from their current assignment."""
        from backend.models import Employee, Site, TemporaryAssignment

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")
        if not employee.current_substitute_assignment or employee.current_substitute_assignment.status != "Active":
            self.raise_bad_request("Employee has no active substitute assignment")

        site_id = employee.current_substitute_assignment.site_id
        end = end_date or date.today()

        employee.current_substitute_assignment.status = "Completed"
        employee.current_substitute_assignment.end_date = datetime.combine(end, datetime.min.time())

        if employee.substitute_assignment_history:
            employee.substitute_assignment_history[-1].status = "Completed"
            employee.substitute_assignment_history[-1].end_date = datetime.combine(end, datetime.min.time())

        start = employee.current_substitute_assignment.start_date
        days = (end - start.date()).days + 1 if start else 1
        employee.total_days_as_substitute += max(1, days)

        employee.substitute_availability = "available"
        employee.current_substitute_assignment = None
        await employee.save()

        site = await Site.find_one(Site.uid == site_id)
        if site and employee_id in site.active_substitute_uids:
            site.active_substitute_uids.remove(employee_id)
            await site.save()

        temp = await TemporaryAssignment.find_one(
            TemporaryAssignment.employee_id == employee_id,
            TemporaryAssignment.site_id == site_id,
            TemporaryAssignment.status == "Active",
        )
        if temp:
            temp.status = "Completed"
            temp.end_date = end
            await temp.save()

        logger.info("Substitute %s released from site %s", employee.name, site_id)

        return {
            "message": "Substitute released successfully",
            "employee_id": employee_id,
            "employee_name": employee.name,
            "days_worked": max(1, days),
        }

    async def update_substitute_profile(self, employee_id: int, update_data: dict) -> dict:
        """Update substitute-specific fields for an outsourced employee."""
        from backend.models import Employee

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")

        for key, value in update_data.items():
            setattr(employee, key, value)

        if update_data.get("can_be_substitute") and not employee.substitute_availability:
            employee.substitute_availability = "available"

        await employee.save()
        logger.info("Substitute profile updated successfully")
        return employee.model_dump(mode="json")

    async def get_substitutes_at_site(self, site_id: int, current_user: dict) -> dict:
        """Get all active substitutes currently assigned to a site."""
        from backend.models import Admin, Employee, Site

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        if current_user.get("role") == "Site Manager":
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if not me or site.assigned_manager_id != me.uid:
                self.raise_forbidden("Access denied")
        elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Access denied")

        substitutes = []
        for uid in site.active_substitute_uids:
            emp = await Employee.find_one(Employee.uid == uid)
            if emp:
                substitutes.append(emp.model_dump(mode="json"))

        return {
            "site_id": site_id,
            "site_name": site.name,
            "active_substitutes": len(substitutes),
            "substitutes": substitutes,
        }
