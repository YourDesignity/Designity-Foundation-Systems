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
        if start_date < date.today():
            self.raise_bad_request("Start date cannot be in the past")
        if end_date < date.today():
            self.raise_bad_request("End date cannot be in the past")

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

    # ====================================================================
    # ROUTER-FACING METHODS
    # ====================================================================

    async def get_available_temp_workers(self) -> dict:
        """Get outsourced workers not currently assigned."""
        from backend.models import Employee

        workers = await Employee.find(
            Employee.employee_type == "Outsourced",
            Employee.status == "Active",
            Employee.is_currently_assigned == False,  # noqa: E712
        ).to_list()

        return {
            "total_available": len(workers),
            "workers": [
                {
                    "id": w.uid,
                    "name": w.name,
                    "designation": w.designation,
                    "phone_kuwait": w.phone_kuwait,
                    "agency_name": w.agency_name,
                    "daily_rate": w.basic_salary,
                    "hourly_rate": w.default_hourly_rate,
                    "availability_status": w.availability_status,
                }
                for w in workers
            ],
        }

    async def get_all_temp_workers(self, available_only: Optional[bool] = None) -> dict:
        """Get all outsourced workers, optionally filtered by availability."""
        from backend.models import Employee

        filters = [Employee.employee_type == "Outsourced"]
        if available_only is True:
            filters.append(Employee.is_currently_assigned == False)  # noqa: E712
        elif available_only is False:
            filters.append(Employee.is_currently_assigned == True)  # noqa: E712

        workers = await Employee.find(*filters).to_list()

        return {
            "total": len(workers),
            "workers": [
                {
                    "id": w.uid,
                    "name": w.name,
                    "designation": w.designation,
                    "phone_kuwait": w.phone_kuwait,
                    "agency_name": w.agency_name,
                    "daily_rate": w.basic_salary,
                    "hourly_rate": w.default_hourly_rate,
                    "availability_status": w.availability_status,
                    "is_currently_assigned": w.is_currently_assigned,
                    "current_site_id": w.current_site_id,
                    "current_site_name": w.current_site_name,
                    "status": w.status,
                }
                for w in workers
            ],
        }

    async def get_cost_summary(
        self,
        site_id: Optional[int] = None,
        project_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> dict:
        """Get cost analysis comparing company vs external labor costs."""
        from backend.models import Employee, TemporaryAssignment

        temp_filters = [TemporaryAssignment.status == "Active"]
        if site_id:
            temp_filters.append(TemporaryAssignment.site_id == site_id)
        if project_id:
            temp_filters.append(TemporaryAssignment.project_id == project_id)

        temp_assignments = await TemporaryAssignment.find(*temp_filters).to_list()

        external_cost_breakdown: list = []
        total_external_cost = 0.0

        for ta in temp_assignments:
            cost = self._calculate_cost(
                ta.rate_type, ta.daily_rate, ta.hourly_rate,
                ta.start_date, ta.end_date,
            )
            total_external_cost += cost
            external_cost_breakdown.append({
                "assignment_id": ta.uid,
                "worker_name": ta.employee_name,
                "site_name": ta.site_name,
                "rate_type": ta.rate_type,
                "rate": ta.daily_rate if ta.rate_type == "Daily" else ta.hourly_rate,
                "start_date": ta.start_date.isoformat(),
                "end_date": ta.end_date.isoformat(),
                "total_days": ta.total_days,
                "cost": round(cost, 3),
            })

        company_filters: list = []
        if site_id:
            company_filters.append(Employee.current_site_id == site_id)
        company_employees = await Employee.find(
            Employee.employee_type == "Company",
            Employee.is_currently_assigned == True,  # noqa: E712
            *company_filters,
        ).to_list()

        total_company_cost = sum((e.basic_salary + e.allowance) for e in company_employees)
        total_labor_cost = total_company_cost + total_external_cost
        external_percentage = (
            round(total_external_cost / total_labor_cost * 100, 2)
            if total_labor_cost > 0 else 0.0
        )

        return {
            "total_company_employees": len(company_employees),
            "total_company_cost": round(total_company_cost, 3),
            "total_external_workers": len(temp_assignments),
            "total_external_cost": round(total_external_cost, 3),
            "total_labor_cost": round(total_labor_cost, 3),
            "external_labor_percentage": external_percentage,
            "external_cost_breakdown": external_cost_breakdown,
        }

    async def register_temp_worker(
        self,
        name: str,
        designation: str,
        phone_kuwait: Optional[str] = None,
        agency_name: Optional[str] = None,
        rate_type: Optional[str] = "Daily",
        daily_rate: Optional[float] = 0.0,
        hourly_rate: Optional[float] = 0.0,
        employee_code: Optional[str] = None,
    ) -> dict:
        """Register a new temporary/outsourced worker."""
        from backend.models import Employee

        new_uid = await self.get_next_uid("employees")
        code = employee_code or f"EXT-{new_uid:03d}"

        new_worker = Employee(
            uid=new_uid,
            name=name,
            designation=designation,
            employee_type="Outsourced",
            phone_kuwait=phone_kuwait,
            agency_name=agency_name,
            basic_salary=daily_rate or 0.0,
            default_hourly_rate=hourly_rate or 0.0,
            status="Active",
            availability_status="Available",
            is_currently_assigned=False,
        )
        await new_worker.insert()
        logger.info("Registered new temp worker: %s (ID: %s)", name, new_uid)

        return {
            "id": new_uid,
            "name": new_worker.name,
            "designation": new_worker.designation,
            "employee_type": new_worker.employee_type,
            "phone_kuwait": new_worker.phone_kuwait,
            "agency_name": new_worker.agency_name,
            "daily_rate": new_worker.basic_salary,
            "hourly_rate": new_worker.default_hourly_rate,
            "availability_status": new_worker.availability_status,
            "employee_code": code,
            "message": f"Worker {name} registered successfully",
        }

    async def bulk_assign_temp_workers(
        self,
        site_id: int,
        workers: list,
        replacement_reason: Optional[str] = None,
        replacing_employee_id: Optional[int] = None,
        replacing_employee_name: Optional[str] = None,
        created_by_admin_id: Optional[int] = None,
    ) -> dict:
        """Bulk assign multiple temp workers to a site."""
        from backend.models import Employee, Project, Site, TemporaryAssignment

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        project = await Project.find_one(Project.uid == site.project_id) if site.project_id else None

        created_assignments: list = []
        failed_assignments: list = []
        total_estimated_cost = 0.0

        for worker_item in workers:
            try:
                employee = await Employee.find_one(Employee.uid == worker_item["employee_id"])
                if not employee:
                    failed_assignments.append({"employee_id": worker_item["employee_id"], "reason": "Worker not found"})
                    continue
                if employee.employee_type != "Outsourced":
                    failed_assignments.append({
                        "employee_id": worker_item["employee_id"],
                        "employee_name": employee.name,
                        "reason": "Worker is not an outsourced employee",
                    })
                    continue

                overlapping = await TemporaryAssignment.find_one(
                    TemporaryAssignment.employee_id == worker_item["employee_id"],
                    TemporaryAssignment.status == "Active",
                    TemporaryAssignment.start_date <= worker_item["end_date"],
                    TemporaryAssignment.end_date >= worker_item["start_date"],
                )
                if overlapping:
                    failed_assignments.append({
                        "employee_id": worker_item["employee_id"],
                        "employee_name": employee.name,
                        "reason": "Worker has an overlapping assignment in this period",
                    })
                    continue

                if worker_item["end_date"] < worker_item["start_date"]:
                    failed_assignments.append({
                        "employee_id": worker_item["employee_id"],
                        "employee_name": employee.name,
                        "reason": "End date must be after start date",
                    })
                    continue

                rate_type = worker_item.get("rate_type") or "Daily"
                daily_rate_val = worker_item.get("daily_rate") if worker_item.get("daily_rate") is not None else employee.basic_salary
                hourly_rate_val = worker_item.get("hourly_rate") if worker_item.get("hourly_rate") is not None else employee.default_hourly_rate
                total_days = (worker_item["end_date"] - worker_item["start_date"]).days + 1
                cost = self._calculate_cost(
                    rate_type, daily_rate_val, hourly_rate_val,
                    worker_item["start_date"], worker_item["end_date"],
                    worker_item.get("total_hours"),
                )
                total_estimated_cost += cost

                new_uid = await self.get_next_uid("temporary_assignments")
                new_assignment = TemporaryAssignment(
                    uid=new_uid,
                    employee_id=worker_item["employee_id"],
                    employee_name=employee.name,
                    employee_type="Outsourced",
                    employee_designation=employee.designation,
                    site_id=site_id,
                    site_name=site.name,
                    project_id=site.project_id or 0,
                    manager_id=site.assigned_manager_id or 0,
                    replacing_employee_id=replacing_employee_id,
                    replacing_employee_name=replacing_employee_name,
                    replacement_reason=replacement_reason,
                    start_date=worker_item["start_date"],
                    end_date=worker_item["end_date"],
                    total_days=total_days,
                    rate_type=rate_type,
                    daily_rate=daily_rate_val,
                    hourly_rate=hourly_rate_val,
                    status="Active",
                    created_by_admin_id=created_by_admin_id,
                )
                await new_assignment.insert()

                employee.is_currently_assigned = True
                employee.current_assignment_type = "Temporary"
                employee.current_project_id = site.project_id
                employee.current_project_name = project.project_name if project else None
                employee.current_site_id = site_id
                employee.current_site_name = site.name
                employee.current_manager_id = site.assigned_manager_id
                employee.current_manager_name = site.assigned_manager_name
                employee.current_assignment_start = worker_item["start_date"]
                employee.current_assignment_end = worker_item["end_date"]
                employee.availability_status = "Assigned"
                if new_assignment.uid not in employee.assignment_history_ids:
                    employee.assignment_history_ids.append(new_assignment.uid)
                await employee.save()

                if worker_item["employee_id"] not in site.assigned_employee_ids:
                    site.assigned_employee_ids.append(worker_item["employee_id"])
                await site.update_workforce_count()

                created_assignments.append({
                    "assignment_id": new_uid,
                    "employee_id": worker_item["employee_id"],
                    "employee_name": employee.name,
                    "start_date": worker_item["start_date"].isoformat(),
                    "end_date": worker_item["end_date"].isoformat(),
                    "total_days": total_days,
                    "rate_type": rate_type,
                    "rate": daily_rate_val if rate_type == "Daily" else hourly_rate_val,
                    "estimated_cost": round(cost, 3),
                })
                logger.info("Temp worker '%s' assigned to site '%s'", employee.name, site.name)

            except Exception:
                logger.error("Error assigning temp worker: assignment failed", exc_info=True)
                failed_assignments.append({
                    "employee_id": worker_item["employee_id"],
                    "reason": "An error occurred during assignment",
                })

        return {
            "message": f"{len(created_assignments)} temp workers assigned successfully",
            "created_count": len(created_assignments),
            "failed_count": len(failed_assignments),
            "total_estimated_cost": round(total_estimated_cost, 3),
            "assignments": created_assignments,
            "failures": failed_assignments,
        }

    async def get_temp_workers_at_site(self, site_id: int) -> dict:
        """Get active temp workers at a site with cost breakdown."""
        from backend.models import Site, TemporaryAssignment

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        active_assignments = await TemporaryAssignment.find(
            TemporaryAssignment.site_id == site_id,
            TemporaryAssignment.status == "Active",
        ).to_list()

        cost_breakdown: list = []
        total_cost = 0.0

        for ta in active_assignments:
            cost = self._calculate_cost(
                ta.rate_type, ta.daily_rate, ta.hourly_rate,
                ta.start_date, ta.end_date,
            )
            total_cost += cost
            cost_breakdown.append({
                "assignment_id": ta.uid,
                "employee_id": ta.employee_id,
                "employee_name": ta.employee_name,
                "designation": ta.employee_designation,
                "rate_type": ta.rate_type,
                "rate": ta.daily_rate if ta.rate_type == "Daily" else ta.hourly_rate,
                "start_date": ta.start_date.isoformat(),
                "end_date": ta.end_date.isoformat(),
                "total_days": ta.total_days,
                "replacement_reason": ta.replacement_reason,
                "estimated_cost": round(cost, 3),
                "status": ta.status,
            })

        return {
            "site_id": site_id,
            "site_name": site.name,
            "total_temp_workers": len(active_assignments),
            "total_cost": round(total_cost, 3),
            "assignments": cost_breakdown,
        }

    async def get_worker_history(self, worker_id: int) -> dict:
        """Get assignment history for a temporary worker."""
        from backend.models import Employee, TemporaryAssignment

        worker = await Employee.find_one(Employee.uid == worker_id)
        if not worker:
            self.raise_not_found("Worker not found")

        assignments = await TemporaryAssignment.find(
            TemporaryAssignment.employee_id == worker_id,
        ).sort("-created_at").to_list()

        total_days_worked = sum(a.total_days for a in assignments if a.status == "Completed")
        total_earnings = sum(
            self._calculate_cost(a.rate_type, a.daily_rate, a.hourly_rate, a.start_date, a.end_date)
            for a in assignments if a.status == "Completed"
        )

        return {
            "worker": {
                "id": worker.uid,
                "name": worker.name,
                "designation": worker.designation,
                "agency_name": worker.agency_name,
                "daily_rate": worker.basic_salary,
                "hourly_rate": worker.default_hourly_rate,
            },
            "total_assignments": len(assignments),
            "active_assignments": len([a for a in assignments if a.status == "Active"]),
            "completed_assignments": len([a for a in assignments if a.status == "Completed"]),
            "total_days_worked": total_days_worked,
            "total_earnings": round(total_earnings, 3),
            "assignments": [
                {
                    "assignment_id": a.uid,
                    "site_name": a.site_name,
                    "start_date": a.start_date.isoformat(),
                    "end_date": a.end_date.isoformat(),
                    "total_days": a.total_days,
                    "rate_type": a.rate_type,
                    "rate": a.daily_rate if a.rate_type == "Daily" else a.hourly_rate,
                    "status": a.status,
                    "replacement_reason": a.replacement_reason,
                }
                for a in assignments
            ],
        }

    async def list_temp_assignments(
        self,
        site_id: Optional[int] = None,
        status: Optional[str] = None,
        start_after: Optional[date] = None,
        end_before: Optional[date] = None,
    ) -> list:
        """Get all temporary assignments with optional filters and cost calculations."""
        from backend.models import TemporaryAssignment

        filters: list = []
        if site_id:
            filters.append(TemporaryAssignment.site_id == site_id)
        if status:
            filters.append(TemporaryAssignment.status == status)
        if start_after:
            filters.append(TemporaryAssignment.start_date >= start_after)
        if end_before:
            filters.append(TemporaryAssignment.end_date <= end_before)

        if filters:
            assignments = await TemporaryAssignment.find(*filters).sort("-created_at").to_list()
        else:
            assignments = await TemporaryAssignment.find_all().sort("-created_at").to_list()

        result = []
        for ta in assignments:
            cost = self._calculate_cost(
                ta.rate_type, ta.daily_rate, ta.hourly_rate,
                ta.start_date, ta.end_date,
            )
            result.append({
                "assignment_id": ta.uid,
                "employee_id": ta.employee_id,
                "employee_name": ta.employee_name,
                "designation": ta.employee_designation,
                "site_id": ta.site_id,
                "site_name": ta.site_name,
                "start_date": ta.start_date.isoformat(),
                "end_date": ta.end_date.isoformat(),
                "total_days": ta.total_days,
                "rate_type": ta.rate_type,
                "rate": ta.daily_rate if ta.rate_type == "Daily" else ta.hourly_rate,
                "estimated_cost": round(cost, 3),
                "status": ta.status,
                "replacement_reason": ta.replacement_reason,
            })
        return result

    async def get_temp_assignment_details(self, assignment_id: int) -> dict:
        """Get temp assignment details with worker and site data."""
        from backend.models import Employee, Site, TemporaryAssignment

        assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
        if not assignment:
            self.raise_not_found("Assignment not found")

        worker = await Employee.find_one(Employee.uid == assignment.employee_id)
        site = await Site.find_one(Site.uid == assignment.site_id)

        cost = self._calculate_cost(
            assignment.rate_type, assignment.daily_rate, assignment.hourly_rate,
            assignment.start_date, assignment.end_date,
        )

        return {
            "assignment": {
                "assignment_id": assignment.uid,
                "employee_id": assignment.employee_id,
                "employee_name": assignment.employee_name,
                "designation": assignment.employee_designation,
                "site_id": assignment.site_id,
                "site_name": assignment.site_name,
                "start_date": assignment.start_date.isoformat(),
                "end_date": assignment.end_date.isoformat(),
                "total_days": assignment.total_days,
                "rate_type": assignment.rate_type,
                "daily_rate": assignment.daily_rate,
                "hourly_rate": assignment.hourly_rate,
                "estimated_cost": round(cost, 3),
                "status": assignment.status,
                "replacement_reason": assignment.replacement_reason,
                "created_at": assignment.created_at.isoformat(),
            },
            "worker": worker,
            "site": site,
        }

    async def update_temp_assignment_fields(self, assignment_id: int, update_data: dict) -> dict:
        """Update a temporary assignment from a dict of changed fields."""
        from backend.models import TemporaryAssignment

        assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
        if not assignment:
            self.raise_not_found("Assignment not found")

        for key, value in update_data.items():
            setattr(assignment, key, value)

        if "start_date" in update_data or "end_date" in update_data:
            assignment.total_days = (assignment.end_date - assignment.start_date).days + 1

        assignment.updated_at = datetime.now()
        await assignment.save()

        cost = self._calculate_cost(
            assignment.rate_type, assignment.daily_rate, assignment.hourly_rate,
            assignment.start_date, assignment.end_date,
        )

        logger.info("Temp assignment %s updated", assignment_id)

        return {
            "assignment_id": assignment.uid,
            "status": assignment.status,
            "start_date": assignment.start_date.isoformat(),
            "end_date": assignment.end_date.isoformat(),
            "total_days": assignment.total_days,
            "estimated_cost": round(cost, 3),
            "message": "Assignment updated successfully",
        }

    async def end_temp_assignment_for_router(self, assignment_id: int) -> dict:
        """End a temporary assignment and return summary with final cost."""
        from backend.models import Employee, Site, TemporaryAssignment

        assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
        if not assignment:
            self.raise_not_found("Assignment not found")

        actual_end = date.today()
        cost = self._calculate_cost(
            assignment.rate_type, assignment.daily_rate, assignment.hourly_rate,
            assignment.start_date, actual_end,
        )

        assignment.status = "Completed"
        assignment.end_date = actual_end
        assignment.total_days = (actual_end - assignment.start_date).days + 1
        assignment.updated_at = datetime.now()
        await assignment.save()

        worker = await Employee.find_one(Employee.uid == assignment.employee_id)
        if worker:
            other_active = await TemporaryAssignment.find(
                TemporaryAssignment.employee_id == assignment.employee_id,
                TemporaryAssignment.status == "Active",
                TemporaryAssignment.uid != assignment_id,
            ).count()
            if other_active == 0:
                worker.is_currently_assigned = False
                worker.current_assignment_type = None
                worker.current_project_id = None
                worker.current_site_id = None
                worker.current_manager_id = None
                worker.availability_status = "Available"
            await worker.save()

        site = await Site.find_one(Site.uid == assignment.site_id)
        if site:
            if assignment.employee_id in site.assigned_employee_ids:
                site.assigned_employee_ids.remove(assignment.employee_id)
            await site.update_workforce_count()

        logger.info("Temp assignment for worker '%s' ended successfully", assignment.employee_name)

        return {
            "message": "Assignment ended successfully",
            "assignment_id": assignment_id,
            "worker_name": assignment.employee_name,
            "actual_end_date": actual_end.isoformat(),
            "total_days": assignment.total_days,
            "final_cost": round(cost, 3),
        }
