"""Service layer for temporary assignment operations."""

import logging
from datetime import date, datetime
from typing import Any, List, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class TemporaryAssignmentService(BaseService):
    """Temporary worker assignment and substitute management."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _calculate_cost(
        rate_type: str,
        daily_rate: float,
        hourly_rate: float,
        start_date: date,
        end_date: date,
        total_hours: Optional[float] = None,
    ) -> float:
        if rate_type == "Hourly":
            hours = total_hours if total_hours is not None else ((end_date - start_date).days + 1) * 8
            return round(hours * hourly_rate, 3)
        days = (end_date - start_date).days + 1
        return round(days * daily_rate, 3)

    # ====================================================================
    # CRUD OPERATIONS
    # ====================================================================

    async def create_temporary_assignment(
        self,
        employee_id: int,
        site_id: int,
        start_date: date,
        end_date: date,
        rate_type: str = "Daily",
        daily_rate: Optional[float] = None,
        hourly_rate: Optional[float] = None,
        total_hours: Optional[float] = None,
        replacement_reason: Optional[str] = None,
        replacing_employee_id: Optional[int] = None,
        replacing_employee_name: Optional[str] = None,
        created_by: Optional[int] = None,
    ):
        """Create a temporary assignment for an outsourced worker."""
        from backend.models import Employee, Project, Site, TemporaryAssignment

        if end_date < start_date:
            self.raise_bad_request("End date must be after start date")

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Worker not found")
        if employee.employee_type != "Outsourced":
            self.raise_bad_request("Worker must be outsourced")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        overlapping = await TemporaryAssignment.find_one(
            TemporaryAssignment.employee_id == employee_id,
            TemporaryAssignment.status == "Active",
            TemporaryAssignment.start_date <= end_date,
            TemporaryAssignment.end_date >= start_date,
        )
        if overlapping:
            self.raise_bad_request("Worker has an overlapping active temporary assignment")

        project = await Project.find_one(Project.uid == site.project_id) if site.project_id else None
        chosen_rate_type = rate_type or "Daily"
        chosen_daily_rate = daily_rate if daily_rate is not None else float(employee.basic_salary or 0.0)
        chosen_hourly_rate = hourly_rate if hourly_rate is not None else float(employee.default_hourly_rate or 0.0)
        total_days = (end_date - start_date).days + 1

        uid = await self.get_next_uid("temporary_assignments")
        assignment = TemporaryAssignment(
            uid=uid,
            employee_id=employee.uid,
            employee_name=employee.name,
            employee_type="Outsourced",
            employee_designation=employee.designation,
            assignment_type="Temporary",
            site_id=site.uid,
            site_name=site.name,
            project_id=site.project_id or 0,
            manager_id=site.assigned_manager_id or 0,
            replacing_employee_id=replacing_employee_id,
            replacing_employee_name=replacing_employee_name,
            replacement_reason=replacement_reason,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            rate_type=chosen_rate_type,
            daily_rate=chosen_daily_rate,
            hourly_rate=chosen_hourly_rate,
            status="Active",
            created_by_admin_id=created_by,
        )
        await assignment.insert()

        employee.is_currently_assigned = True
        employee.current_assignment_type = "Temporary"
        employee.current_project_id = site.project_id
        employee.current_project_name = project.project_name if project else site.project_name
        employee.current_site_id = site.uid
        employee.current_site_name = site.name
        employee.current_manager_id = site.assigned_manager_id
        employee.current_manager_name = site.assigned_manager_name
        employee.current_assignment_start = start_date
        employee.current_assignment_end = end_date
        employee.availability_status = "Assigned"
        employee.substitute_availability = "assigned"
        if assignment.uid not in employee.assignment_history_ids:
            employee.assignment_history_ids.append(assignment.uid)
        await employee.save()

        if employee.uid not in site.assigned_employee_ids:
            site.assigned_employee_ids.append(employee.uid)
        if employee.uid not in site.active_substitute_uids:
            site.active_substitute_uids.append(employee.uid)
        await site.update_workforce_count()

        logger.info("Temporary assignment created: %s -> %s (ID: %s)", employee.name, site.name, uid)
        return assignment

    async def get_temporary_assignment_by_id(self, assignment_id: int):
        """Get temporary assignment by UID."""
        from backend.models import TemporaryAssignment

        assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
        if not assignment:
            self.raise_not_found("Temporary assignment not found")
        return assignment

    async def extend_temporary_assignment(self, assignment_id: int, new_end_date: date, updated_by: Optional[int] = None):
        """Extend temporary assignment end date."""
        assignment = await self.get_temporary_assignment_by_id(assignment_id)
        if assignment.status != "Active":
            self.raise_bad_request("Only active assignments can be extended")
        extension_end = new_end_date.date() if isinstance(new_end_date, datetime) else new_end_date
        if extension_end <= assignment.end_date.date():
            self.raise_bad_request("New end date must be after current end date")

        assignment.end_date = extension_end
        assignment.total_days = (assignment.end_date - assignment.start_date).days + 1
        assignment.updated_at = datetime.now()
        await assignment.save()

        logger.info("Temporary assignment extended: %s by user %s", assignment_id, updated_by)
        return assignment

    async def end_temporary_assignment(self, assignment_id: int, end_date: Optional[date] = None, ended_by: Optional[int] = None):
        """Mark temporary assignment completed and release worker."""
        from backend.models import Employee, Site, TemporaryAssignment

        assignment = await self.get_temporary_assignment_by_id(assignment_id)
        if assignment.status != "Active":
            self.raise_bad_request("Assignment is not active")

        actual_end = end_date or date.today()
        if actual_end < assignment.start_date.date():
            self.raise_bad_request("End date cannot be before start date")

        assignment.status = "Completed"
        assignment.end_date = actual_end
        assignment.total_days = (assignment.end_date - assignment.start_date).days + 1
        assignment.updated_at = datetime.now()
        await assignment.save()

        worker = await Employee.find_one(Employee.uid == assignment.employee_id)
        if worker:
            other_active = await TemporaryAssignment.find(
                TemporaryAssignment.employee_id == worker.uid,
                TemporaryAssignment.status == "Active",
                TemporaryAssignment.uid != assignment.uid,
            ).count()
            if other_active == 0:
                worker.is_currently_assigned = False
                worker.current_assignment_type = None
                worker.current_project_id = None
                worker.current_project_name = None
                worker.current_site_id = None
                worker.current_site_name = None
                worker.current_manager_id = None
                worker.current_manager_name = None
                worker.current_assignment_start = None
                worker.current_assignment_end = None
                worker.availability_status = "Available"
                worker.substitute_availability = "available"
            await worker.save()

        site = await Site.find_one(Site.uid == assignment.site_id)
        if site:
            if assignment.employee_id in site.assigned_employee_ids:
                site.assigned_employee_ids.remove(assignment.employee_id)
            if assignment.employee_id in site.active_substitute_uids:
                site.active_substitute_uids.remove(assignment.employee_id)
            await site.update_workforce_count()

        logger.info("Temporary assignment ended: %s by user %s", assignment_id, ended_by)
        return assignment

    # ====================================================================
    # SUBSTITUTE OPERATIONS
    # ====================================================================

    async def find_available_substitutes(
        self,
        designation: Optional[str] = None,
        site_id: Optional[int] = None,
        exclude_employee_id: Optional[int] = None,
    ) -> List:
        """Find outsourced workers available for substitute duty."""
        from backend.models import Employee

        filters = [
            Employee.employee_type == "Outsourced",
            Employee.status == "Active",
            Employee.is_currently_assigned == False,
        ]
        if designation:
            filters.append(Employee.designation == designation)

        workers = await Employee.find(*filters).to_list()
        if exclude_employee_id is not None:
            workers = [w for w in workers if w.uid != exclude_employee_id]
        if site_id is not None:
            workers = [w for w in workers if w.current_site_id in (None, site_id)]
        return workers

    async def assign_substitute(
        self,
        absent_employee_id: int,
        substitute_employee_id: int,
        site_id: int,
        start_date: date,
        end_date: date,
        reason: str,
        assigned_by: Optional[int] = None,
    ):
        """Assign substitute employee to replace an absent employee."""
        from backend.models import Employee

        absent = await Employee.find_one(Employee.uid == absent_employee_id)
        if not absent:
            self.raise_not_found("Absent employee not found")

        substitute = await Employee.find_one(Employee.uid == substitute_employee_id)
        if not substitute:
            self.raise_not_found("Substitute employee not found")

        assignment = await self.create_temporary_assignment(
            employee_id=substitute_employee_id,
            site_id=site_id,
            start_date=start_date,
            end_date=end_date,
            rate_type="Daily",
            daily_rate=substitute.basic_salary,
            replacement_reason=reason,
            replacing_employee_id=absent.uid,
            replacing_employee_name=absent.name,
            created_by=assigned_by,
        )

        substitute.can_be_substitute = True
        substitute.substitute_availability = "assigned"
        substitute.total_substitute_assignments = (substitute.total_substitute_assignments or 0) + 1
        substitute.total_days_as_substitute = (substitute.total_days_as_substitute or 0) + assignment.total_days
        substitute.current_substitute_assignment = {
            "site_id": site_id,
            "site_name": assignment.site_name,
            "start_date": assignment.start_date,
            "end_date": assignment.end_date,
            "reason": reason,
            "replacing_employee_id": absent.uid,
            "replacing_employee_name": absent.name,
            "assigned_by_manager_id": assigned_by or 0,
            "daily_rate": assignment.daily_rate,
            "hourly_rate": assignment.hourly_rate,
            "status": "Active",
        }
        await substitute.save()

        logger.info("Substitute assigned: %s replacing %s", substitute.uid, absent.uid)
        return assignment

    async def mark_substitute_available(self, employee_id: int):
        """Mark outsourced worker available for substitute duty."""
        from backend.models import Employee

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")
        employee.can_be_substitute = True
        employee.substitute_availability = "available"
        employee.current_substitute_assignment = None
        await employee.save()
        return employee

    async def mark_substitute_unavailable(self, employee_id: int, reason: Optional[str] = None):
        """Mark substitute unavailable for new assignments."""
        from backend.models import Employee

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")
        employee.can_be_substitute = True
        employee.substitute_availability = "unavailable"
        if reason:
            employee.current_substitute_assignment = {
                "site_id": employee.current_site_id or 0,
                "site_name": employee.current_site_name,
                "start_date": datetime.now(),
                "end_date": None,
                "reason": reason,
                "replacing_employee_id": None,
                "replacing_employee_name": None,
                "assigned_by_manager_id": 0,
                "daily_rate": employee.basic_salary,
                "hourly_rate": employee.default_hourly_rate,
                "status": "Cancelled",
            }
        await employee.save()
        return employee

    # ====================================================================
    # REPORTS
    # ====================================================================

    async def calculate_temporary_worker_costs(self, assignment_id: int) -> dict:
        """Calculate projected/final cost for one temporary assignment."""
        assignment = await self.get_temporary_assignment_by_id(assignment_id)
        cost = self._calculate_cost(
            assignment.rate_type,
            assignment.daily_rate,
            assignment.hourly_rate,
            assignment.start_date.date(),
            assignment.end_date.date(),
        )
        return {
            "assignment_id": assignment.uid,
            "employee_id": assignment.employee_id,
            "employee_name": assignment.employee_name,
            "site_id": assignment.site_id,
            "rate_type": assignment.rate_type,
            "daily_rate": assignment.daily_rate,
            "hourly_rate": assignment.hourly_rate,
            "total_days": assignment.total_days,
            "total_cost": cost,
            "status": assignment.status,
        }

    async def calculate_total_temp_costs(
        self,
        site_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> dict:
        """Calculate aggregate temporary labor costs."""
        from backend.models import TemporaryAssignment

        filters = []
        if site_id is not None:
            filters.append(TemporaryAssignment.site_id == site_id)
        assignments = await (TemporaryAssignment.find(*filters).to_list() if filters else TemporaryAssignment.find_all().to_list())

        rows = []
        total = 0.0
        for assignment in assignments:
            start = assignment.start_date.date()
            if month and start.month != month:
                continue
            if year and start.year != year:
                continue
            cost = self._calculate_cost(
                assignment.rate_type,
                assignment.daily_rate,
                assignment.hourly_rate,
                assignment.start_date.date(),
                assignment.end_date.date(),
            )
            total += cost
            rows.append({"assignment_id": assignment.uid, "employee_name": assignment.employee_name, "cost": cost})

        return {"count": len(rows), "total_cost": round(total, 3), "items": rows}

    async def get_active_temporary_assignments(self, site_id: Optional[int] = None) -> List:
        """List active temporary assignments."""
        from backend.models import TemporaryAssignment

        filters = [TemporaryAssignment.status == "Active"]
        if site_id is not None:
            filters.append(TemporaryAssignment.site_id == site_id)
        return await TemporaryAssignment.find(*filters).sort("-created_at").to_list()

    async def get_substitute_usage_report(self, month: int, year: int) -> dict:
        """Monthly substitute usage summary."""
        active = await self.get_active_temporary_assignments()
        completed = []
        total_cost = 0.0
        for assignment in active:
            if assignment.start_date.month == month and assignment.start_date.year == year:
                cost = self._calculate_cost(
                    assignment.rate_type,
                    assignment.daily_rate,
                    assignment.hourly_rate,
                    assignment.start_date.date(),
                    assignment.end_date.date(),
                )
                total_cost += cost
                completed.append(
                    {
                        "assignment_id": assignment.uid,
                        "substitute_name": assignment.employee_name,
                        "replacing_employee_id": assignment.replacing_employee_id,
                        "replacing_employee_name": assignment.replacing_employee_name,
                        "site_id": assignment.site_id,
                        "site_name": assignment.site_name,
                        "reason": assignment.replacement_reason,
                        "total_days": assignment.total_days,
                        "cost": cost,
                    }
                )

        return {
            "month": month,
            "year": year,
            "total_substitute_assignments": len(completed),
            "total_cost": round(total_cost, 3),
            "assignments": completed,
        }

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def get_temporary_assignments(self):
        """Backward-compatible helper for listing all temporary assignments."""
        from backend.models import TemporaryAssignment

        return await TemporaryAssignment.find_all().sort("-created_at").to_list()

    async def update_temporary_assignment(self, assignment_id: int, payload: Any):
        """Backward-compatible update helper."""
        assignment = await self.get_temporary_assignment_by_id(assignment_id)
        data = self._to_dict(payload)
        for field, value in data.items():
            setattr(assignment, field, value)
        if "start_date" in data or "end_date" in data:
            assignment.total_days = (assignment.end_date - assignment.start_date).days + 1
        assignment.updated_at = datetime.now()
        await assignment.save()
        return assignment

    async def delete_temporary_assignment(self, assignment_id: int) -> bool:
        """Backward-compatible hard delete helper."""
        assignment = await self.get_temporary_assignment_by_id(assignment_id)
        await assignment.delete()
        logger.info("Temporary assignment deleted: %s", assignment_id)
        return True
