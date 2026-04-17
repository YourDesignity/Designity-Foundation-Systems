from fastapi import APIRouter
from typing import List
from backend.models import InventoryItem
from backend.services import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])
service = InventoryService()

@router.get("/", response_model=List[InventoryItem])
async def get_inventory():
    """Get all inventory items."""
    return await service.get_all_inventory()

@router.post("/")
async def add_item(item: InventoryItem):
    """Add new inventory item."""
    return await service.add_inventory_item(item)

@router.delete("/{uid}")
async def delete_item(uid: int):
    """Delete inventory item."""
    return await service.delete_inventory_item(uid)
