"""Service layer for inventory management."""

import logging
from typing import Any

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class InventoryService(BaseService):
    """Business logic for inventory CRUD."""

    async def get_all_inventory(self) -> list:
        from backend.models import InventoryItem

        return await InventoryItem.find_all().to_list()

    async def add_inventory_item(self, item_data: Any):
        from backend.models import InventoryItem

        payload = item_data.model_dump(exclude_unset=True) if hasattr(item_data, "model_dump") else dict(item_data)
        payload["uid"] = await self.get_next_uid("inventory_items")

        stock = payload.get("stock", 0)
        if stock == 0:
            payload["status"] = "Out of Stock"
        elif stock < 10:
            payload["status"] = "Low Stock"
        else:
            payload["status"] = "In Stock"

        item = InventoryItem(**payload)
        await item.create()
        logger.info("Created inventory item uid=%s name=%s", item.uid, item.name)
        return item

    async def delete_inventory_item(self, uid: int) -> dict:
        from backend.models import InventoryItem

        item = await InventoryItem.find_one(InventoryItem.uid == uid)
        if not item:
            self.raise_not_found("Item not found")
        await item.delete()
        logger.info("Deleted inventory item uid=%s", uid)
        return {"message": "Item deleted"}

    async def get_inventory(self):
        """Backward-compatible alias."""
        return await self.get_all_inventory()

    async def add_item(self, item: Any):
        """Backward-compatible alias."""
        return await self.add_inventory_item(item)

    async def delete_item(self, uid: int):
        """Backward-compatible alias."""
        return await self.delete_inventory_item(uid)
