"""Service layer for project site operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class SiteService(BaseService):
    """Site CRUD and assignment operations."""

    async def create_site(self, payload: Any):
        from backend.models import Site

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("sites")
        site = Site(**data)
        await site.insert()
        return site

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
        return site

    async def delete_site(self, site_id: int) -> bool:
        site = await self.get_site_by_id(site_id)
        await site.delete()
        return True
