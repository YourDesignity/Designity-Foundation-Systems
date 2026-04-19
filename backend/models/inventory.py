"""Inventory models."""

from typing import List, Optional

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
    # Sample pictures of the material/item
    image_urls: List[str] = []
    # Project/Contract/Site links
    project_id: Optional[int] = None
    contract_id: Optional[int] = None
    site_id: Optional[int] = None

    class Settings:
        name = "inventory_items"
