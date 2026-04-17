"""Service layer for manager profile operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class ManagerService(BaseService):
    """Site manager profile CRUD and lifecycle operations."""

    async def create_manager_profile(self, payload: Any):
        from backend.models import ManagerProfile

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("manager_profiles")
        profile = ManagerProfile(**data)
        await profile.insert()
        return profile

    async def get_manager_profile(self, manager_id: int):
        from backend.models import ManagerProfile

        profile = await ManagerProfile.find_one(ManagerProfile.uid == manager_id)
        if not profile:
            self.raise_not_found(f"Manager profile {manager_id} not found")
        return profile

    async def get_manager_profiles(self):
        from backend.models import ManagerProfile

        return await ManagerProfile.find_all().sort("+uid").to_list()

    async def update_manager_profile(self, manager_id: int, payload: Any):
        profile = await self.get_manager_profile(manager_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(profile, field, value)
        await profile.save()
        return profile

    async def deactivate_manager(self, manager_id: int):
        profile = await self.get_manager_profile(manager_id)
        profile.is_active = False
        await profile.save()
        return profile
