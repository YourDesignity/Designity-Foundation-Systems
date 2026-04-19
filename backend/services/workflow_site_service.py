"""Service layer for workflow site operations."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class WorkflowSiteService(BaseService):
    """Business logic for workflow site CRUD, manager/employee assignments, activity."""

    async def get_available_managers(self, current_user: dict) -> list[dict]:
        from backend.models import Admin

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can view managers")

        managers = await Admin.find(Admin.role == "Site Manager", Admin.is_active == True).to_list()
        return [
            {"uid": m.uid, "full_name": m.full_name, "email": m.email, "role": m.role}
            for m in managers
        ]

    async def create_site(self, site_data: Any, current_user: dict) -> dict:
        from backend.models import Project, Contract, Site, CompanySettings

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can create sites")

        project = await Project.find_one(Project.uid == site_data.project_id)
        if not project:
            self.raise_not_found("Project not found")

        contract = await Contract.find_one(Contract.uid == site_data.contract_id)
        if not contract:
            self.raise_not_found("Contract not found")

        if contract.project_id != site_data.project_id:
            self.raise_bad_request("Contract does not belong to the specified project")

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)

        new_uid = await self.get_next_uid("sites")
        if settings and settings.auto_generate_site_codes:
            prefix = settings.site_code_prefix or "SITE"
            site_code = f"{prefix}-{new_uid:03d}"
        else:
            site_code = f"SITE-{new_uid:03d}"

        new_site = Site(
            uid=new_uid,
            site_code=site_code,
            name=site_data.site_name,
            location=site_data.location,
            description=site_data.description,
            project_id=site_data.project_id,
            project_name=project.project_name,
            contract_id=site_data.contract_id,
            contract_code=contract.contract_code,
            required_workers=site_data.required_workers,
            status="Active",
        )

        await new_site.insert()

        if new_site.uid not in project.site_ids:
            project.site_ids.append(new_site.uid)
            await project.save()

        if new_site.uid not in contract.site_ids:
            contract.site_ids.append(new_site.uid)
            await contract.save()

        return new_site.model_dump(mode="json")

    async def get_all_sites(
        self,
        current_user: dict,
        project_id: Optional[int] = None,
        contract_id: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        from backend.models import Site, Admin

        if current_user.get("role") == "Site Manager":
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if not me:
                self.raise_not_found("Manager profile not found")
            # Support both single-manager (legacy) and multi-manager fields
            sites = await Site.find(
                {"$or": [{"assigned_manager_id": me.uid}, {"assigned_manager_ids": me.uid}]}
            ).to_list()

        elif current_user.get("role") in ["SuperAdmin", "Admin"]:
            filters = []
            if project_id:
                filters.append(Site.project_id == project_id)
            if contract_id:
                filters.append(Site.contract_id == contract_id)
            if status_filter:
                filters.append(Site.status == status_filter)

            if filters:
                sites = await Site.find(*filters).sort("+uid").to_list()
            else:
                sites = await Site.find_all().sort("+uid").to_list()
        else:
            self.raise_forbidden("Access denied")

        return [s.model_dump(mode="json") for s in sites]

    async def get_site_details(self, site_id: int, current_user: dict) -> dict:
        from backend.models import Site, Admin, EmployeeAssignment, Employee

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        if current_user.get("role") == "Site Manager":
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if not me or (site.assigned_manager_id != me.uid and me.uid not in site.assigned_manager_ids):
                self.raise_forbidden("Access denied")
        elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Access denied")

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.site_id == site_id,
            EmployeeAssignment.status == "Active",
        ).to_list()

        employees = []
        for assignment in assignments:
            emp = await Employee.find_one(Employee.uid == assignment.employee_id)
            if emp:
                employees.append(emp)

        return {
            "site": site.model_dump(mode="json"),
            "assigned_employees": [e.model_dump(mode="json") for e in employees],
            "assignments": [a.model_dump(mode="json") for a in assignments],
        }

    async def update_site(self, site_id: int, site_update: Any, current_user: dict) -> dict:
        from backend.models import Site

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can update sites")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        update_data = site_update.model_dump(exclude_unset=True)
        if "site_name" in update_data:
            update_data["name"] = update_data.pop("site_name")
        for key, value in update_data.items():
            setattr(site, key, value)

        await site.save()

        return site.model_dump(mode="json")

    async def delete_site(self, site_id: int, current_user: dict) -> None:
        from backend.models import Site, Project, Contract, EmployeeAssignment

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can delete sites")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        active_assignments = await EmployeeAssignment.find(
            EmployeeAssignment.site_id == site_id,
            EmployeeAssignment.status == "Active",
        ).count()

        if active_assignments > 0:
            self.raise_bad_request(f"Cannot delete site with {active_assignments} active employee assignment(s).")

        if site.project_id:
            project = await Project.find_one(Project.uid == site.project_id)
            if project and site.uid in project.site_ids:
                project.site_ids.remove(site.uid)
                await project.save()

        if site.contract_id:
            contract = await Contract.find_one(Contract.uid == site.contract_id)
            if contract and site.uid in contract.site_ids:
                contract.site_ids.remove(site.uid)
                await contract.save()

        await site.delete()

    async def assign_manager(self, site_id: int, manager_id: int, current_user: dict) -> dict:
        from backend.models import Site, Admin

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can assign managers")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        manager = await Admin.find_one(Admin.uid == manager_id)
        if not manager or manager.role != "Site Manager":
            self.raise_bad_request("Invalid manager ID: must be an active Site Manager")

        site.assigned_manager_id = manager_id
        site.assigned_manager_name = manager.full_name
        # Maintain multi-manager list: if manager not already in list, add them
        if manager_id not in site.assigned_manager_ids:
            site.assigned_manager_ids.append(manager_id)
            site.assigned_manager_names.append(manager.full_name)
        await site.save()

        return {
            "message": "Manager assigned successfully",
            "site_id": site_id,
            "site_name": site.name,
            "manager_id": manager_id,
            "manager_name": manager.full_name,
        }

    async def unassign_manager(self, site_id: int, current_user: dict) -> None:
        from backend.models import Site

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can unassign managers")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        site.assigned_manager_id = None
        site.assigned_manager_name = None
        site.assigned_manager_ids = []
        site.assigned_manager_names = []
        await site.save()

    async def add_manager(self, site_id: int, manager_id: int, current_user: dict) -> dict:
        """Add an additional manager to a site (multi-manager support)."""
        from backend.models import Site, Admin

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can assign managers")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        manager = await Admin.find_one(Admin.uid == manager_id)
        if not manager or manager.role != "Site Manager":
            self.raise_bad_request("Invalid manager ID: must be an active Site Manager")

        if manager_id in site.assigned_manager_ids:
            return {
                "message": "Manager already assigned to this site",
                "site_id": site_id,
                "site_name": site.name,
                "manager_id": manager_id,
                "manager_name": manager.full_name,
                "assigned_manager_ids": site.assigned_manager_ids,
                "assigned_manager_names": site.assigned_manager_names,
            }

        site.assigned_manager_ids.append(manager_id)
        site.assigned_manager_names.append(manager.full_name)

        # Keep legacy primary manager in sync (first manager in list)
        if site.assigned_manager_id is None:
            site.assigned_manager_id = manager_id
            site.assigned_manager_name = manager.full_name

        await site.save()

        return {
            "message": "Manager added successfully",
            "site_id": site_id,
            "site_name": site.name,
            "manager_id": manager_id,
            "manager_name": manager.full_name,
            "assigned_manager_ids": site.assigned_manager_ids,
            "assigned_manager_names": site.assigned_manager_names,
        }

    async def remove_manager(self, site_id: int, manager_id: int, current_user: dict) -> None:
        """Remove a specific manager from a site's manager list."""
        from backend.models import Site

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can remove managers")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        if manager_id not in site.assigned_manager_ids and site.assigned_manager_id != manager_id:
            self.raise_not_found("Manager is not assigned to this site")

        # Remove from list
        if manager_id in site.assigned_manager_ids:
            idx = site.assigned_manager_ids.index(manager_id)
            site.assigned_manager_ids.pop(idx)
            if idx < len(site.assigned_manager_names):
                site.assigned_manager_names.pop(idx)

        # Update legacy primary manager field
        if site.assigned_manager_id == manager_id:
            site.assigned_manager_id = site.assigned_manager_ids[0] if site.assigned_manager_ids else None
            site.assigned_manager_name = site.assigned_manager_names[0] if site.assigned_manager_names else None

        await site.save()

    async def get_site_employees(self, site_id: int, current_user: dict) -> dict:
        from backend.models import Site, Admin, EmployeeAssignment, Employee

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        if current_user.get("role") == "Site Manager":
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if not me or (site.assigned_manager_id != me.uid and me.uid not in site.assigned_manager_ids):
                self.raise_forbidden("Access denied")
        elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Access denied")

        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.site_id == site_id,
            EmployeeAssignment.status == "Active",
        ).to_list()

        employees = []
        for assignment in assignments:
            emp = await Employee.find_one(Employee.uid == assignment.employee_id)
            if emp:
                employees.append(emp)

        return {
            "site": site.model_dump(mode="json"),
            "employees": [e.model_dump(mode="json") for e in employees],
            "assignments": [a.model_dump(mode="json") for a in assignments],
            "total_assigned": len(employees),
            "required_workers": site.required_workers,
        }

    async def assign_employees(self, site_id: int, request: Any, current_user: dict) -> dict:
        from backend.models import Site, Project, EmployeeAssignment, Employee

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can assign employees")

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        try:
            start = date.fromisoformat(request.assignment_start)
        except ValueError:
            self.raise_bad_request("Invalid assignment_start date format (use YYYY-MM-DD)")

        end = None
        if request.assignment_end:
            try:
                end = date.fromisoformat(request.assignment_end)
            except ValueError:
                self.raise_bad_request("Invalid assignment_end date format (use YYYY-MM-DD)")

        project = await Project.find_one(Project.uid == site.project_id) if site.project_id else None
        created = []
        failed = []

        for emp_id in request.employee_ids:
            employee = await Employee.find_one(Employee.uid == emp_id)
            if not employee:
                failed.append({"employee_id": emp_id, "reason": "Employee not found"})
                continue

            existing = await EmployeeAssignment.find_one(
                EmployeeAssignment.employee_id == emp_id,
                EmployeeAssignment.site_id == site_id,
                EmployeeAssignment.status == "Active",
            )
            if existing:
                failed.append({"employee_id": emp_id, "employee_name": employee.name, "reason": "Already assigned to this site"})
                continue

            new_uid = await self.get_next_uid("employee_assignments")
            assignment = EmployeeAssignment(
                uid=new_uid,
                employee_id=emp_id,
                employee_name=employee.name,
                employee_designation=employee.designation,
                employee_type=employee.employee_type,
                assignment_type="Permanent",
                project_id=site.project_id,
                project_name=project.project_name if project else None,
                contract_id=site.contract_id,
                site_id=site_id,
                site_name=site.name,
                manager_id=site.assigned_manager_id,
                manager_name=site.assigned_manager_name,
                assigned_date=date.today(),
                assignment_start=start,
                assignment_end=end,
                status="Active",
                created_by_admin_id=current_user.get("id"),
            )
            await assignment.insert()

            employee.is_currently_assigned = True
            employee.current_assignment_type = "Permanent"
            employee.current_project_id = site.project_id
            employee.current_project_name = project.project_name if project else None
            employee.current_site_id = site_id
            employee.current_site_name = site.name
            employee.current_manager_id = site.assigned_manager_id
            employee.current_manager_name = site.assigned_manager_name
            employee.current_assignment_start = start
            employee.current_assignment_end = end
            employee.availability_status = "Assigned"
            if assignment.uid not in employee.assignment_history_ids:
                employee.assignment_history_ids.append(assignment.uid)
            await employee.save()

            if emp_id not in site.assigned_employee_ids:
                site.assigned_employee_ids.append(emp_id)

            created.append(assignment.model_dump(mode="json"))

        await site.update_workforce_count()

        return {
            "message": f"{len(created)} employees assigned successfully",
            "created_count": len(created),
            "failed_count": len(failed),
            "assignments": created,
            "failures": failed,
        }

    async def remove_employee(self, site_id: int, employee_id: int, current_user: dict) -> None:
        from backend.models import Site, EmployeeAssignment, Employee

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can remove employees")

        assignment = await EmployeeAssignment.find_one(
            EmployeeAssignment.employee_id == employee_id,
            EmployeeAssignment.site_id == site_id,
            EmployeeAssignment.status == "Active",
        )
        if not assignment:
            self.raise_not_found("Active assignment not found for this employee at this site")

        assignment.status = "Completed"
        assignment.assignment_end = date.today()
        assignment.updated_at = datetime.now()
        await assignment.save()

        employee = await Employee.find_one(Employee.uid == employee_id)
        if employee:
            other_active = await EmployeeAssignment.find(
                EmployeeAssignment.employee_id == employee_id,
                EmployeeAssignment.status == "Active",
            ).count()
            if other_active == 0:
                employee.is_currently_assigned = False
                employee.current_site_id = None
                employee.availability_status = "Available"
            await employee.save()

        site = await Site.find_one(Site.uid == site_id)
        if site:
            if employee_id in site.assigned_employee_ids:
                site.assigned_employee_ids.remove(employee_id)
            await site.update_workforce_count()

    async def get_site_activity(self, site_id: int, limit: int, current_user: dict) -> dict:
        from backend.models import Site, Admin, EmployeeAssignment, TemporaryAssignment

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        if current_user.get("role") == "Site Manager":
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if not me or (site.assigned_manager_id != me.uid and me.uid not in site.assigned_manager_ids):
                self.raise_forbidden("Access denied")
        elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Access denied")

        emp_assignments = await EmployeeAssignment.find(
            EmployeeAssignment.site_id == site_id
        ).sort("-uid").limit(limit).to_list()

        temp_assignments = await TemporaryAssignment.find(
            TemporaryAssignment.site_id == site_id
        ).sort("-uid").limit(limit).to_list()

        activities = []

        for a in emp_assignments:
            activities.append({
                "type": "employee_assigned" if a.status == "Active" else "employee_unassigned",
                "description": f"{a.employee_name} ({a.employee_designation}) assigned to this site",
                "date": a.assigned_date.isoformat() if a.assigned_date else (a.created_at.isoformat() if a.created_at else None),
                "status": a.status,
                "employee_name": a.employee_name,
                "employee_type": a.employee_type,
            })

        for t in temp_assignments:
            activities.append({
                "type": "temp_worker_assigned" if t.status == "Active" else "temp_worker_ended",
                "description": f"Temporary worker {t.employee_name} assigned to this site",
                "date": t.start_date.isoformat() if t.start_date else (t.created_at.isoformat() if t.created_at else None),
                "status": t.status,
                "employee_name": t.employee_name,
                "employee_type": "Temporary",
            })

        activities.sort(key=lambda x: x["date"] or "", reverse=True)

        return {
            "site_id": site_id,
            "site_name": site.name,
            "activities": activities[:limit],
            "total": len(activities),
        }
