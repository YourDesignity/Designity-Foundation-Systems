import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from typing import List
from backend.models import InventoryItem
from backend.security import get_current_active_user
from backend.services import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])
service = InventoryService()

INVENTORY_PHOTOS_DIR = os.path.join("backend", "uploads", "inventory_photos")
os.makedirs(INVENTORY_PHOTOS_DIR, exist_ok=True)


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


@router.post("/{uid}/photos")
async def upload_inventory_photo(
    uid: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Upload a sample picture for an inventory item."""
    item = await InventoryItem.find_one(InventoryItem.uid == uid)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Use a server-generated UUID path — no user-controlled data in the filename
    filename = f"inv_{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(INVENTORY_PHOTOS_DIR, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    url = f"/uploads/inventory_photos/{filename}"
    item.image_urls.append(url)
    await item.save()
    return {"message": "Photo uploaded", "url": url, "image_urls": item.image_urls}


@router.delete("/{uid}/photos")
async def delete_inventory_photo(
    uid: int,
    url: str = Query(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Remove a photo URL from an inventory item."""
    item = await InventoryItem.find_one(InventoryItem.uid == uid)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    item.image_urls = [u for u in item.image_urls if u != url]
    await item.save()
    return {"message": "Photo removed", "image_urls": item.image_urls}

