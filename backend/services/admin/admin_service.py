"""Service layer for admin management operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class AdminService(BaseService):
    """Admin CRUD and account operations."""

    async def create_admin(self, payload: Any):
        from backend.models import Admin

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("admins")
        admin = Admin(**data)
        await admin.insert()
        return admin

    async def get_admin_by_id(self, admin_id: int):
        from backend.models import Admin

        admin = await Admin.find_one(Admin.uid == admin_id)
        if not admin:
            self.raise_not_found(f"Admin {admin_id} not found")
        return admin

    async def get_all_admins(self):
        from backend.models import Admin

        return await Admin.find_all().sort("+uid").to_list()

    async def update_admin(self, admin_id: int, payload: Any):
        admin = await self.get_admin_by_id(admin_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(admin, field, value)
        await admin.save()
        return admin

    async def delete_admin(self, admin_id: int) -> bool:
        admin = await self.get_admin_by_id(admin_id)
        await admin.delete()
        return True

    async def get_active_managers(self):
        from backend.models import Admin

        return await Admin.find(Admin.role == "Site Manager", Admin.is_active == True).sort("+uid").to_list()
