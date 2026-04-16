"""Inventory models."""

from typing import Optional

from beanie import Document

from backend.models.base import MemoryNode


class InventoryItem(Document, MemoryNode):
    name: str
    category: str
    stock: int
    unit: str
    price: float
    supplier: Optional[str] = None
    status: str = "In Stock"

    class Settings:
        name = "inventory_items"
