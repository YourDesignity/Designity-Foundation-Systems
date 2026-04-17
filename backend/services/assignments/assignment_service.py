"""Service layer for permanent employee assignments."""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class AssignmentService(BaseService):
    """Employee assignment business logic."""

    # ====================================================================
    # CRUD OPERATIONS
    # ====================================================================

    async def create_assignment(
        self,
        employee_id: int,
        site_id: int,
        contract_id: Optional[int],
        start_date: date,
        end_date: Optional[date] = None,
        designation: Optional[str] = None,
        daily_rate: Optional[float] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ):
        """Create a permanent assignment for a company employee."""
        from backend.models import Contract, Employee, EmployeeAssignment, Project, Site

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")
        if employee.status != "Active":
            self.raise_bad_request(f"Employee '{employee.name}' is not active")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        contract = None
        if contract_id is not None:
            contract = await Contract.find_one(Contract.uid == contract_id)
            if not contract:
                self.raise_not_found("Contract not found")

        if start_date < date.today():
            self.raise_bad_request("Start date cannot be in the past")
        if end_date and end_date <= start_date:
            self.raise_bad_request("End date must be after start date")

        conflicts = await self.check_assignment_conflicts(employee_id, start_date, end_date)
        if conflicts:
            details = ", ".join([f"Site {c.site_id}" for c in conflicts])
            self.raise_bad_request(f"Employee already has overlapping assignments: {details}")

        project = await Project.find_one(Project.uid == site.project_id) if site.project_id else None
        uid = await self.get_next_uid("employee_assignments")
        assignment_notes = notes or ""
        if daily_rate is not None:
            assignment_notes = (f"{assignment_notes}\nDaily rate override: {daily_rate}").strip()

        assignment = EmployeeAssignment(
            uid=uid,
            employee_id=employee.uid,
            employee_name=employee.name,
            employee_type=employee.employee_type,
            employee_designation=designation or employee.designation,
            assignment_type="Permanent",
            project_id=site.project_id,
            project_name=project.project_name if project else site.project_name,
            contract_id=contract.uid if contract else site.contract_id,
            site_id=site.uid,
            site_name=site.name,
            manager_id=site.assigned_manager_id,
            manager_name=site.assigned_manager_name,
            assigned_date=date.today(),
            assignment_start=start_date,
            assignment_end=end_date,
            status="Active",
            notes=assignment_notes or None,
            created_by_admin_id=created_by,
        )
        await assignment.insert()

        employee.is_currently_assigned = True
        employee.current_assignment_type = "Permanent"
        employee.current_project_id = assignment.project_id
        employee.current_project_name = assignment.project_name
        employee.current_site_id = assignment.site_id
        employee.current_site_name = assignment.site_name
        employee.current_manager_id = assignment.manager_id
        employee.current_manager_name = assignment.manager_name
        employee.current_assignment_start = assignment.assignment_start
        employee.current_assignment_end = assignment.assignment_end
        employee.availability_status = "Assigned"
        if assignment.uid not in employee.assignment_history_ids:
            employee.assignment_history_ids.append(assignment.uid)
        await employee.save()

        if employee.uid not in site.assigned_employee_ids:
            site.assigned_employee_ids.append(employee.uid)
        await site.update_workforce_count()

        logger.info("Assignment created: %s -> site %s (ID: %s)", employee.name, site.name, uid)
        return assignment

    async def get_assignment_by_id(self, assignment_id: int):
        """Get assignment by UID."""
        from backend.models import EmployeeAssignment

        assignment = await EmployeeAssignment.find_one(EmployeeAssignment.uid == assignment_id)
        if not assignment:
            self.raise_not_found("Assignment not found")
        return assignment

    async def update_assignment(
        self,
        assignment_id: int,
        end_date: Optional[date] = None,
        daily_rate: Optional[float] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        updated_by: Optional[int] = None,
    ):
        """Update mutable assignment fields (period/status/notes)."""
        assignment = await self.get_assignment_by_id(assignment_id)

        if end_date is not None:
            start = assignment.assignment_start.date() if isinstance(assignment.assignment_start, datetime) else assignment.assignment_start
            if end_date <= start:
                self.raise_bad_request("End date must be after start date")
            assignment.assignment_end = end_date

        if status is not None:
            valid_statuses = {"Active", "Completed", "Terminated", "Reassigned"}
            if status not in valid_statuses:
                self.raise_bad_request(f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}")
            assignment.status = status

        merged_notes = assignment.notes or ""
        if daily_rate is not None:
            merged_notes = (f"{merged_notes}\nDaily rate override: {daily_rate}").strip()
        if notes:
            merged_notes = (f"{merged_notes}\n{notes}").strip()
        if merged_notes:
            assignment.notes = merged_notes

        assignment.updated_at = datetime.now()
        await assignment.save()
        logger.info("Assignment updated: %s by user %s", assignment_id, updated_by)
        return assignment

    async def terminate_assignment(
        self,
        assignment_id: int,
        reason: str,
        termination_date: Optional[date] = None,
        terminated_by: Optional[int] = None,
    ):
        """Terminate an assignment and release linked employee/site state."""
        from backend.models import Employee, Site

        assignment = await self.get_assignment_by_id(assignment_id)
        if assignment.status == "Terminated":
            self.raise_bad_request("Assignment already terminated")

        term_date = termination_date or date.today()
        start = assignment.assignment_start.date() if isinstance(assignment.assignment_start, datetime) else assignment.assignment_start
        if term_date < start:
            self.raise_bad_request("Termination date cannot be before start date")

        assignment.assignment_end = term_date
        assignment.status = "Terminated"
        assignment.termination_reason = reason
        assignment.notes = f"{assignment.notes or ''}\nTerminated: {reason}".strip()
        assignment.updated_at = datetime.now()
        await assignment.save()

        employee = await Employee.find_one(Employee.uid == assignment.employee_id)
        if employee:
            other_active = await self.get_employee_assignments(employee.uid, active_only=True)
            if not [row for row in other_active if row.uid != assignment.uid]:
                employee.is_currently_assigned = False
                employee.current_assignment_type = None
                employee.current_project_id = None
                employee.current_project_name = None
                employee.current_site_id = None
                employee.current_site_name = None
                employee.current_manager_id = None
                employee.current_manager_name = None
                employee.current_assignment_start = None
                employee.current_assignment_end = None
                employee.availability_status = "Available"
                await employee.save()

        site = await Site.find_one(Site.uid == assignment.site_id)
        if site and assignment.employee_id in site.assigned_employee_ids:
            site.assigned_employee_ids.remove(assignment.employee_id)
            await site.update_workforce_count()

        logger.warning("Assignment terminated: %s reason=%s by user %s", assignment_id, reason, terminated_by)
        return assignment

    # ====================================================================
    # QUERIES
    # ====================================================================

    async def get_employee_assignments(self, employee_id: int, active_only: bool = True) -> List:
        """Get assignments for one employee."""
        from backend.models import EmployeeAssignment

        filters = [EmployeeAssignment.employee_id == employee_id]
        if active_only:
            filters.append(EmployeeAssignment.status == "Active")
        return await EmployeeAssignment.find(*filters).sort("-created_at").to_list()

    async def get_site_assignments(self, site_id: int, active_only: bool = True) -> List:
        """Get assignments for one site."""
        from backend.models import EmployeeAssignment

        filters = [EmployeeAssignment.site_id == site_id]
        if active_only:
            filters.append(EmployeeAssignment.status == "Active")
        return await EmployeeAssignment.find(*filters).sort("-created_at").to_list()

    async def get_contract_assignments(self, contract_id: int, active_only: bool = True) -> List:
        """Get assignments for one contract."""
        from backend.models import EmployeeAssignment

        filters = [EmployeeAssignment.contract_id == contract_id]
        if active_only:
            filters.append(EmployeeAssignment.status == "Active")
        return await EmployeeAssignment.find(*filters).sort("-created_at").to_list()

    async def get_active_assignments(self) -> List:
        """Get every active assignment."""
        from backend.models import EmployeeAssignment

        return await EmployeeAssignment.find(EmployeeAssignment.status == "Active").sort("-created_at").to_list()

    # ====================================================================
    # VALIDATION & BUSINESS LOGIC
    # ====================================================================

    async def check_assignment_conflicts(self, employee_id: int, start_date: date, end_date: Optional[date] = None) -> List:
        """Return active assignments that overlap with a date range."""
        assignments = await self.get_employee_assignments(employee_id, active_only=True)
        check_end = end_date or date(2099, 12, 31)

        conflicts = []
        for assignment in assignments:
            assignment_start = (
                assignment.assignment_start.date() if isinstance(assignment.assignment_start, datetime) else assignment.assignment_start
            )
            assignment_end = (
                assignment.assignment_end.date()
                if isinstance(assignment.assignment_end, datetime)
                else assignment.assignment_end
            ) or date(2099, 12, 31)
            if start_date <= assignment_end and check_end >= assignment_start:
                conflicts.append(assignment)
        return conflicts

    async def transfer_employee(
        self,
        employee_id: int,
        from_site_id: int,
        to_site_id: int,
        transfer_date: date,
        transferred_by: Optional[int] = None,
    ):
        """Transfer an employee from one site to another."""
        current = await self.get_site_assignments(from_site_id, active_only=True)
        current = [row for row in current if row.employee_id == employee_id]
        if not current:
            self.raise_not_found("Active assignment not found for transfer")

        current_assignment = current[0]
        await self.terminate_assignment(
            current_assignment.uid,
            reason=f"Transferred to site {to_site_id}",
            termination_date=transfer_date - timedelta(days=1),
            terminated_by=transferred_by,
        )

        new_assignment = await self.create_assignment(
            employee_id=employee_id,
            site_id=to_site_id,
            contract_id=current_assignment.contract_id,
            start_date=transfer_date,
            designation=current_assignment.employee_designation,
            notes=f"Transferred from site {from_site_id}",
            created_by=transferred_by,
        )
        logger.info("Employee transfer completed from site %s to site %s", from_site_id, to_site_id)
        return new_assignment

    # ====================================================================
    # REPORTS
    # ====================================================================

    async def get_assignment_history(self, employee_id: int) -> List[dict]:
        """Get chronological assignment history for an employee."""
        assignments = await self.get_employee_assignments(employee_id, active_only=False)
        assignments = sorted(assignments, key=lambda row: row.assignment_start)
        history = []
        for assignment in assignments:
            start = assignment.assignment_start.date() if isinstance(assignment.assignment_start, datetime) else assignment.assignment_start
            end_value = assignment.assignment_end.date() if isinstance(assignment.assignment_end, datetime) else assignment.assignment_end
            history.append(
                {
                    "assignment_id": assignment.uid,
                    "site_id": assignment.site_id,
                    "site_name": assignment.site_name,
                    "contract_id": assignment.contract_id,
                    "project_name": assignment.project_name,
                    "designation": assignment.employee_designation,
                    "start_date": start.isoformat() if start else None,
                    "end_date": end_value.isoformat() if end_value else None,
                    "status": assignment.status,
                    "notes": assignment.notes,
                }
            )
        return history

    async def calculate_assignment_costs(self, assignment_id: int) -> dict:
        """Calculate estimated assignment cost using employee monthly salary fallback."""
        from backend.models import Employee

        assignment = await self.get_assignment_by_id(assignment_id)
        employee = await Employee.find_one(Employee.uid == assignment.employee_id)

        start = assignment.assignment_start.date() if isinstance(assignment.assignment_start, datetime) else assignment.assignment_start
        end_value = assignment.assignment_end.date() if isinstance(assignment.assignment_end, datetime) else assignment.assignment_end
        end = end_value or date.today()
        total_days = (end - start).days + 1

        if employee and employee.standard_work_days > 0:
            daily_rate = employee.basic_salary / employee.standard_work_days
        elif employee:
            daily_rate = employee.basic_salary
        else:
            daily_rate = 0.0

        total_cost = round(daily_rate * total_days, 3)
        return {
            "assignment_id": assignment.uid,
            "employee_id": assignment.employee_id,
            "employee_name": assignment.employee_name,
            "daily_rate": round(daily_rate, 3),
            "total_days": total_days,
            "total_cost": total_cost,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }

    # --------------------------------------------------------------------
    # Backward compatible aliases
    # --------------------------------------------------------------------

    async def get_assignments(self):
        """Backward-compatible alias for all assignments."""
        from backend.models import EmployeeAssignment

        return await EmployeeAssignment.find_all().sort("-created_at").to_list()

    async def delete_assignment(self, assignment_id: int) -> bool:
        """Backward-compatible hard delete helper."""
        assignment = await self.get_assignment_by_id(assignment_id)
        await assignment.delete()
        logger.info("Assignment deleted: %s", assignment_id)
        return True
