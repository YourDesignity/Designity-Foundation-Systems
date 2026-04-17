"""Service layer for manager site operations."""

import logging
from datetime import datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ManagerSiteService(BaseService):
    """Business logic for manager sites, employees, and attendance."""

    async def _verify_manager_access(self, manager_id: int, current_user: dict) -> None:
        from backend.models import Admin

        if current_user.get("role") == "Site Manager":
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if not me or me.uid != manager_id:
                self.raise_forbidden("Access denied")
        elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Access denied")

    async def get_manager_sites(self, manager_id: int, current_user: dict) -> dict:
        from backend.models import Admin, Site, EmployeeAssignment

        await self._verify_manager_access(manager_id, current_user)

        manager = await Admin.find_one(Admin.uid == manager_id)
        if not manager:
            self.raise_not_found("Manager not found")

        sites = await Site.find(Site.assigned_manager_id == manager_id).to_list()

        site_summaries = []
        for site in sites:
            assignments = await EmployeeAssignment.find(
                EmployeeAssignment.site_id == site.uid,
                EmployeeAssignment.status == "Active",
            ).count()

            site_dict = site.model_dump(mode="json")
            site_dict["active_employees"] = assignments
            site_dict["is_understaffed"] = site.is_understaffed
            site_dict["headcount_shortage"] = site.headcount_shortage
            site_summaries.append(site_dict)

        return {
            "manager_id": manager_id,
            "manager_name": manager.full_name,
            "total_sites": len(sites),
            "sites": site_summaries,
        }

    async def get_site_employees(self, manager_id: int, site_id: int, current_user: dict) -> dict:
        from backend.models import Admin, Site, Employee, EmployeeAssignment

        await self._verify_manager_access(manager_id, current_user)

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        if site.assigned_manager_id != manager_id and current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("This manager is not assigned to this site")

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.site_id == site_id,
            EmployeeAssignment.status == "Active",
        ).to_list()

        employees = []
        for assignment in assignments:
            emp = await Employee.find_one(Employee.uid == assignment.employee_id)
            if emp:
                employees.append({
                    "employee": emp.model_dump(mode="json"),
                    "assignment": assignment.model_dump(mode="json"),
                })

        substitutes = []
        for uid in site.active_substitute_uids:
            emp = await Employee.find_one(Employee.uid == uid)
            if emp:
                substitutes.append(emp.model_dump(mode="json"))

        return {
            "site": site.model_dump(mode="json"),
            "company_employees": employees,
            "substitutes": substitutes,
            "total_workers": len(employees) + len(substitutes),
            "required_workers": site.required_workers,
            "is_understaffed": site.is_understaffed,
        }

    async def record_attendance(self, manager_id: int, site_id: int, request: Any, current_user: dict) -> dict:
        from backend.models import Admin, Site, Employee, Attendance

        await self._verify_manager_access(manager_id, current_user)

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        if site.assigned_manager_id != manager_id and current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("This manager is not assigned to this site")

        manager = await Admin.find_one(Admin.uid == manager_id)

        created = []
        updated = []
        failed = []

        for record in request.records:
            try:
                employee = await Employee.find_one(Employee.uid == record.employee_uid)
                if not employee:
                    failed.append({"employee_uid": record.employee_uid, "reason": "Employee not found"})
                    continue

                existing = await Attendance.find_one(
                    Attendance.employee_uid == record.employee_uid,
                    Attendance.date == request.date,
                    Attendance.site_uid == site_id,
                )

                if existing:
                    existing.status = record.status
                    existing.shift = record.shift
                    existing.overtime_hours = record.overtime_hours
                    existing.is_replacement = record.is_substitute
                    existing.replacing_employee_id = record.replacing_employee_id
                    existing.replacement_reason = record.leave_reason
                    existing.recorded_by_manager_id = manager_id
                    existing.recorded_by_manager_name = manager.full_name if manager else None
                    existing.is_substitute = record.is_substitute
                    existing.leave_type = record.leave_type
                    existing.leave_reason = record.leave_reason
                    existing.substitute_requested = record.substitute_requested
                    existing.notes = record.notes
                    existing.recorded_at = datetime.now()
                    await existing.save()
                    updated.append(existing.model_dump(mode="json"))
                else:
                    new_uid = await self.get_next_uid("attendance")
                    attendance = Attendance(
                        uid=new_uid,
                        employee_uid=record.employee_uid,
                        site_uid=site_id,
                        date=request.date,
                        status=record.status,
                        shift=record.shift,
                        overtime_hours=record.overtime_hours,
                        is_replacement=record.is_substitute,
                        replacing_employee_id=record.replacing_employee_id,
                        replacement_reason=record.leave_reason,
                        recorded_by_manager_id=manager_id,
                        recorded_by_manager_name=manager.full_name if manager else None,
                        is_substitute=record.is_substitute,
                        leave_type=record.leave_type,
                        leave_reason=record.leave_reason,
                        substitute_requested=record.substitute_requested,
                        notes=record.notes,
                        recorded_at=datetime.now(),
                    )
                    await attendance.insert()
                    created.append(attendance.model_dump(mode="json"))

            except Exception as e:
                logger.error("Error recording attendance for employee %s: %s", record.employee_uid, e)
                failed.append({"employee_uid": record.employee_uid, "reason": "Failed to record attendance"})

        return {
            "message": f"Attendance recorded: {len(created)} new, {len(updated)} updated",
            "site_id": site_id,
            "date": request.date,
            "created_count": len(created),
            "updated_count": len(updated),
            "failed_count": len(failed),
            "records": created + updated,
            "failures": failed,
        }

    async def get_attendance(self, manager_id: int, site_id: int, attendance_date: Optional[str], current_user: dict) -> dict:
        from backend.models import Attendance

        await self._verify_manager_access(manager_id, current_user)

        filters = [Attendance.site_uid == site_id]
        if attendance_date:
            filters.append(Attendance.date == attendance_date)

        records = await Attendance.find(*filters).sort("-date").to_list()

        return {
            "site_id": site_id,
            "date": attendance_date,
            "total_records": len(records),
            "records": [r.model_dump(mode="json") for r in records],
        }
