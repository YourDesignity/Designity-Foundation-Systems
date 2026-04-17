"""Service layer for supplier operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class SupplierService(BaseService):
    """Supplier CRUD and lookup operations."""

    async def create_supplier(self, payload: Any):
        from backend.models import Supplier

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("suppliers")
        supplier = Supplier(**data)
        await supplier.insert()
        return supplier

    async def get_supplier_by_id(self, supplier_id: int):
        from backend.models import Supplier

        supplier = await Supplier.find_one(Supplier.uid == supplier_id)
        if not supplier:
            self.raise_not_found(f"Supplier {supplier_id} not found")
        return supplier

    async def get_suppliers(self):
        from backend.models import Supplier

        return await Supplier.find_all().sort("+uid").to_list()

    async def update_supplier(self, supplier_id: int, payload: Any):
        supplier = await self.get_supplier_by_id(supplier_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(supplier, field, value)
        await supplier.save()
        return supplier

    async def delete_supplier(self, supplier_id: int) -> bool:
        supplier = await self.get_supplier_by_id(supplier_id)
        await supplier.delete()
        return True
