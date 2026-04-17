from fastapi import APIRouter, HTTPException
from typing import List
from backend.models import InventoryItem
from backend.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])
service = InventoryService()

@router.get("/", response_model=List[InventoryItem])
async def get_inventory():
    return await service.get_inventory()

@router.post("/")
async def add_item(item: InventoryItem):
    return await service.add_item(item)

@router.delete("/{uid}")
async def delete_item(uid: int):
    return await service.delete_item(uid)