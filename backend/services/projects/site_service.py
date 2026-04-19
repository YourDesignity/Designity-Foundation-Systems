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

    async def get_active_sites_for_listing(self) -> list[dict]:
        from backend.models import Admin, Site

        sites = await Site.find(Site.is_active == True).sort(+Site.name).to_list()
        manager_uids = [s.manager_uid for s in sites if s.manager_uid]
        managers = await Admin.find(Admin.uid.in_(manager_uids)).to_list() if manager_uids else []
        manager_map = {m.uid: m.full_name for m in managers}
        return [
            {
                "id": site.uid,
                "name": site.name,
                "location": site.location,
                "site_manager": manager_map.get(site.manager_uid) if site.manager_uid else None,
                "description": site.description,
                "phone": site.phone,
                "is_active": site.is_active,
            }
            for site in sites
        ]

    async def create_legacy_site(self, payload: Any) -> dict:
        from backend.models import Admin, Site

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        site_name = data.get("name")
        existing = await Site.find_one(Site.name == site_name)
        if existing:
            self.raise_bad_request(f"The site name '{site_name}' is already taken.")

        manager_uid = None
        manager_name = data.get("site_manager")
        if manager_name:
            admin = await Admin.find_one(Admin.full_name == manager_name)
            if admin:
                manager_uid = admin.uid

        new_uid = await self.get_next_uid("sites")
        site = Site(
            uid=new_uid,
            name=site_name,
            location=data.get("location"),
            manager_uid=manager_uid,
            description=data.get("description"),
            phone=data.get("phone"),
            is_active=True,
        )
        await site.insert()
        logger.info("Legacy site created: %s (%s)", site_name, new_uid)
        return {"status": "success", "site_id": new_uid}

    async def delete_legacy_site(self, site_id: int) -> None:
        from backend.models import Admin, Site

        site = await Site.find_one(Site.uid == site_id)
        if not site:
            self.raise_not_found("Site Not Found")

        admins_with_access = await Admin.find(Admin.assigned_site_uids == site_id).to_list()
        for admin in admins_with_access:
            if site_id in admin.assigned_site_uids:
                admin.assigned_site_uids.remove(site_id)
                await admin.save()

        await site.delete()
        logger.info("Legacy site deleted: %s", site_id)

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
