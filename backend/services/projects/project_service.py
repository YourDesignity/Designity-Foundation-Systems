"""Service layer for project business operations."""

import logging
from datetime import datetime
from typing import Any

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ProjectService(BaseService):
    """Business logic for project creation, costing, and progress."""

    async def create_project(self, payload: Any, created_by_admin_id: int | None = None):
        """
        Create a project.

        Validations:
        - project_name and client_name are required
        - Project code is generated from company settings

        Args:
            payload: Project payload
            created_by_admin_id: Admin UID

        Returns:
            Created project document
        """
        from backend.models import CompanySettings, Project

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        if not data.get("project_name"):
            self.raise_bad_request("project_name is required")
        if not data.get("client_name"):
            self.raise_bad_request("client_name is required")

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)
        new_uid = await self.get_next_uid("projects")
        prefix = (settings.project_code_prefix if settings and settings.auto_generate_project_codes else "PRJ") or "PRJ"
        project_code = f"{prefix}-{new_uid:03d}"

        project = Project(
            uid=new_uid,
            project_code=project_code,
            project_name=data["project_name"],
            client_name=data["client_name"],
            client_contact=data.get("client_contact"),
            client_email=data.get("client_email"),
            description=data.get("description"),
            status=data.get("status", "Active"),
            created_by_admin_id=created_by_admin_id or data.get("created_by_admin_id"),
        )
        await project.insert()
        logger.info("Project created: %s (%s)", project.project_code, project.project_name)
        return project

    async def calculate_project_cost(self, project_id: int) -> dict:
        """
        Calculate total project cost from contracts and temporary workforce costs.

        Args:
            project_id: Project UID

        Returns:
            Project cost breakdown
        """
        from backend.models import Contract, Project, TemporaryAssignment

        project = await Project.find_one(Project.uid == project_id)
        if not project:
            self.raise_not_found("Project not found")

        contracts = await Contract.find(Contract.project_id == project_id).to_list()
        contract_value_total = sum(float(c.contract_value or 0.0) for c in contracts)

        temp_assignments = await TemporaryAssignment.find(
            TemporaryAssignment.project_id == project_id,
            TemporaryAssignment.status == "Active",
        ).to_list()
        temp_workforce_cost = sum((ta.daily_rate or 0.0) * (ta.total_days or 0) for ta in temp_assignments)

        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "contract_value_total": contract_value_total,
            "temporary_workforce_cost": temp_workforce_cost,
            "total_estimated_cost": contract_value_total + temp_workforce_cost,
            "contract_count": len(contracts),
            "active_temp_assignments": len(temp_assignments),
        }

    async def get_project_progress(self, project_id: int) -> dict:
        """
        Get project progress/fulfillment metrics.

        Args:
            project_id: Project UID

        Returns:
            Progress summary payload
        """
        from backend.models import EmployeeAssignment, Project, Site, TemporaryAssignment

        project = await Project.find_one(Project.uid == project_id)
        if not project:
            self.raise_not_found("Project not found")

        sites = await Site.find(Site.project_id == project_id).to_list()
        total_required = sum(site.required_workers for site in sites)
        total_assigned = sum(site.assigned_workers for site in sites)

        company_assignments = await EmployeeAssignment.find(
            EmployeeAssignment.project_id == project_id,
            EmployeeAssignment.employee_type == "Company",
            EmployeeAssignment.status == "Active",
        ).count()
        external_assignments = await TemporaryAssignment.find(
            TemporaryAssignment.project_id == project_id,
            TemporaryAssignment.status == "Active",
        ).count()

        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "status": project.status,
            "total_sites": len(sites),
            "total_required_workers": total_required,
            "total_assigned_workers": total_assigned,
            "company_employees": company_assignments,
            "external_workers": external_assignments,
            "fulfillment_rate": (total_assigned / total_required * 100) if total_required > 0 else 0,
        }

    async def get_project_by_id(self, project_id: int):
        from backend.models import Project

        project = await Project.find_one(Project.uid == project_id)
        if not project:
            self.raise_not_found(f"Project {project_id} not found")
        return project

    async def get_projects(self):
        from backend.models import Project

        return await Project.find_all().sort("+uid").to_list()

    async def get_projects_filtered(self, status: str | None = None):
        from backend.models import Project

        if status:
            return await Project.find(Project.status == status).sort("+uid").to_list()
        return await Project.find_all().sort("+uid").to_list()

    async def get_project_details(self, project_id: int) -> dict:
        from backend.models import Contract, EmployeeAssignment, Project, Site

        project = await Project.find_one(Project.uid == project_id)
        if not project:
            self.raise_not_found("Project not found")

        await project.update_metrics()
        contracts = await Contract.find(Contract.project_id == project_id).to_list()
        sites = await Site.find(Site.project_id == project_id).to_list()
        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.project_id == project_id,
            EmployeeAssignment.status == "Active",
        ).to_list()
        return {
            "project": project,
            "contracts": contracts,
            "sites": sites,
            "active_assignments": assignments,
        }

    async def update_project(self, project_id: int, payload: Any):
        project = await self.get_project_by_id(project_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(project, field, value)
        project.updated_at = datetime.now()
        await project.save()
        logger.info("Project updated: ID %s", project_id)
        return project

    async def delete_project(self, project_id: int) -> bool:
        project = await self.get_project_by_id(project_id)
        await project.delete()
        logger.info("Project deleted: ID %s", project_id)
        return True

    async def delete_project_with_constraints(self, project_id: int) -> bool:
        from backend.models import Contract, Site

        project = await self.get_project_by_id(project_id)

        active_contracts = await Contract.find(
            Contract.project_id == project_id,
            Contract.status == "Active",
        ).count()
        if active_contracts > 0:
            self.raise_bad_request(
                f"Cannot delete project with {active_contracts} active contract(s). Complete or terminate contracts first."
            )

        active_sites = await Site.find(
            Site.project_id == project_id,
            Site.status == "Active",
        ).count()
        if active_sites > 0:
            self.raise_bad_request(f"Cannot delete project with {active_sites} active site(s).")

        await project.delete()
        logger.info("Project deleted with constraints: ID %s", project_id)
        return True

    async def get_project_workforce_summary(self, project_id: int) -> dict:
        summary = await self.get_project_progress(project_id)
        return {
            "project_id": summary["project_id"],
            "project_name": summary["project_name"],
            "total_sites": summary["total_sites"],
            "total_required_workers": summary["total_required_workers"],
            "total_assigned_workers": summary["total_assigned_workers"],
            "company_employees": summary["company_employees"],
            "external_workers": summary["external_workers"],
            "fulfillment_rate": summary["fulfillment_rate"],
        }
