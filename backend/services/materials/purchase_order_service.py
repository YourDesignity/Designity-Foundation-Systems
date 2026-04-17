"""Service layer for purchase order operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class PurchaseOrderService(BaseService):
    """Purchase order CRUD and status operations."""

    async def create_purchase_order(self, payload: Any):
        from backend.models import PurchaseOrder

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("purchase_orders")
        po = PurchaseOrder(**data)
        await po.insert()
        return po

    async def get_purchase_order_by_id(self, po_id: int):
        from backend.models import PurchaseOrder

        po = await PurchaseOrder.find_one(PurchaseOrder.uid == po_id)
        if not po:
            self.raise_not_found(f"Purchase order {po_id} not found")
        return po

    async def get_purchase_orders(self):
        from backend.models import PurchaseOrder

        return await PurchaseOrder.find_all().sort("+uid").to_list()

    async def update_purchase_order(self, po_id: int, payload: Any):
        po = await self.get_purchase_order_by_id(po_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(po, field, value)
        await po.save()
        return po

    async def delete_purchase_order(self, po_id: int) -> bool:
        po = await self.get_purchase_order_by_id(po_id)
        await po.delete()
        return True
