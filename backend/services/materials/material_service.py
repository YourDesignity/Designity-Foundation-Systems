"""Service layer for material operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class MaterialService(BaseService):
    """Material CRUD and stock operations."""

    async def create_material(self, payload: Any):
        from backend.models import Material

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("materials")
        material = Material(**data)
        await material.insert()
        return material

    async def get_material_by_id(self, material_id: int):
        from backend.models import Material

        material = await Material.find_one(Material.uid == material_id)
        if not material:
            self.raise_not_found(f"Material {material_id} not found")
        return material

    async def get_materials(self):
        from backend.models import Material

        return await Material.find_all().sort("+uid").to_list()

    async def update_material(self, material_id: int, payload: Any):
        material = await self.get_material_by_id(material_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(material, field, value)
        await material.save()
        return material

    async def delete_material(self, material_id: int) -> bool:
        material = await self.get_material_by_id(material_id)
        await material.delete()
        return True
