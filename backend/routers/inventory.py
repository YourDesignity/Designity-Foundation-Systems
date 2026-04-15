from fastapi import APIRouter, HTTPException
from typing import List
from backend.models import InventoryItem
from backend.database import get_next_uid

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("/", response_model=List[InventoryItem])
async def get_inventory():
    return await InventoryItem.find_all().to_list()

@router.post("/")
async def add_item(item: InventoryItem):
    item.uid = await get_next_uid("inventory_items")
    # Auto-status logic
    if item.stock == 0: item.status = "Out of Stock"
    elif item.stock < 10: item.status = "Low Stock"
    else: item.status = "In Stock"
    
    await item.create()
    return item

@router.delete("/{uid}")
async def delete_item(uid: int):
    item = await InventoryItem.find_one(InventoryItem.uid == uid)
    if not item: raise HTTPException(404, "Item not found")
    await item.delete()
    return {"message": "Item deleted"}