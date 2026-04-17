"""Service layer for project site operations."""

import logging
from typing import Any, Optional

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class SiteService(BaseService):
    """Business logic for site lifecycle and staffing-capacity checks."""

    async def create_site(self, payload: Any):
        """
        Create a workflow site linked to project and contract.

        Validations:
        - Project and contract must exist
        - Contract must belong to provided project

        Args:
            payload: Site creation payload

        Returns:
            Created site document
        """
        from backend.models import CompanySettings, Contract, Project, Site

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

        project_id = data.get("project_id")
        contract_id = data.get("contract_id")
        project = await Project.find_one(Project.uid == project_id) if project_id is not None else None
        contract = await Contract.find_one(Contract.uid == contract_id) if contract_id is not None else None
        if project_id is not None and not project:
            self.raise_not_found("Project not found")
        if contract_id is not None and not contract:
            self.raise_not_found("Contract not found")
        if project and contract and contract.project_id != project.uid:
            self.raise_bad_request("Contract does not belong to the specified project")

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)
        new_uid = await self.get_next_uid("sites")
        prefix = (settings.site_code_prefix if settings and settings.auto_generate_site_codes else "SITE") or "SITE"
        site_code = data.get("site_code") or f"{prefix}-{new_uid:03d}"

        site = Site(
            uid=new_uid,
            site_code=site_code,
            name=data.get("site_name") or data.get("name", ""),
            location=data.get("location", ""),
            description=data.get("description"),
            project_id=project.uid if project else None,
            project_name=project.project_name if project else None,
            contract_id=contract.uid if contract else None,
            contract_code=contract.contract_code if contract else None,
            required_workers=int(data.get("required_workers", 0)),
            status=data.get("status", "Active"),
        )
        await site.insert()

        if project and site.uid not in project.site_ids:
            project.site_ids.append(site.uid)
            await project.save()
        if contract and site.uid not in contract.site_ids:
            contract.site_ids.append(site.uid)
            await contract.save()

        logger.info("Site created: %s (ID: %s)", site.site_code, site.uid)
        return site

    async def check_site_capacity(self, site_id: int) -> dict:
        """
        Check workforce capacity and shortage status for a site.

        Args:
            site_id: Site UID

        Returns:
            Capacity summary payload
        """
        from backend.models import Site

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site not found")

        return {
            "site_id": site.uid,
            "site_name": site.name,
            "required_workers": site.required_workers,
            "assigned_workers": site.assigned_workers,
            "substitute_workers": len(site.active_substitute_uids),
            "current_headcount": site.current_headcount,
            "is_understaffed": site.is_understaffed,
            "headcount_shortage": site.headcount_shortage,
        }

    async def get_understaffed_sites(
        self,
        project_id: Optional[int] = None,
        contract_id: Optional[int] = None,
    ) -> list[dict]:
        """
        Get all currently understaffed sites.

        Args:
            project_id: Optional project filter
            contract_id: Optional contract filter

        Returns:
            Understaffed site summaries
        """
        from backend.models import Site

        filters = []
        if project_id is not None:
            filters.append(Site.project_id == project_id)
        if contract_id is not None:
            filters.append(Site.contract_id == contract_id)

        sites = await (Site.find(*filters).to_list() if filters else Site.find_all().to_list())
        return [
            {
                "site_id": site.uid,
                "site_code": site.site_code,
                "site_name": site.name,
                "project_id": site.project_id,
                "contract_id": site.contract_id,
                "required_workers": site.required_workers,
                "current_headcount": site.current_headcount,
                "headcount_shortage": site.headcount_shortage,
            }
            for site in sites
            if site.is_understaffed
        ]

    async def get_site_by_id(self, site_id: int):
        from backend.models import Site

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found(f"Site {site_id} not found")
        return site

    async def get_sites(self):
        from backend.models import Site

        return await Site.find_all().sort("+uid").to_list()

    async def update_site(self, site_id: int, payload: Any):
        site = await self.get_site_by_id(site_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(site, field, value)
        await site.save()
        logger.info("Site updated: ID %s", site_id)
        return site

    async def delete_site(self, site_id: int) -> bool:
        site = await self.get_site_by_id(site_id)
        await site.delete()
        logger.info("Site deleted: ID %s", site_id)
        return True
