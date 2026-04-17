"""Service layer for designations and wage metadata."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class DesignationService(BaseService):
    """Designation CRUD and lookup operations."""

    async def create_designation(self, payload: Any):
        from backend.models import Designation

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("designations")
        designation = Designation(**data)
        await designation.insert()
        return designation

    async def get_designation_by_id(self, designation_id: int):
        from backend.models import Designation

        designation = await Designation.find_one(Designation.uid == designation_id)
        if not designation:
            self.raise_not_found(f"Designation {designation_id} not found")
        return designation

    async def get_designations(self):
        from backend.models import Designation

        return await Designation.find_all().sort("+uid").to_list()

    async def update_designation(self, designation_id: int, payload: Any):
        designation = await self.get_designation_by_id(designation_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(designation, field, value)
        await designation.save()
        return designation

    async def delete_designation(self, designation_id: int) -> bool:
        designation = await self.get_designation_by_id(designation_id)
        await designation.delete()
        return True
