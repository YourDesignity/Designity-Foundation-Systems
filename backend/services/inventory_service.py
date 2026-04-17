"""Service layer for inventory management."""

import logging
from typing import Any

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class InventoryService(BaseService):
    """Business logic for inventory CRUD."""

    async def get_inventory(self):
        from backend.models import InventoryItem

        return await InventoryItem.find_all().to_list()

    async def add_item(self, item: Any):
        from backend.models import InventoryItem

        item.uid = await self.get_next_uid("inventory_items")

        if item.stock == 0:
            item.status = "Out of Stock"
        elif item.stock < 10:
            item.status = "Low Stock"
        else:
            item.status = "In Stock"

        await item.create()
        return item

    async def delete_item(self, uid: int):
        from backend.models import InventoryItem

        item = await InventoryItem.find_one(InventoryItem.uid == uid)
        if not item:
            self.raise_not_found("Item not found")
        await item.delete()
        return {"message": "Item deleted"}
