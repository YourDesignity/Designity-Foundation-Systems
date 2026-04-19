"""
Item Catalogue CRUD router — admin-managed predefined item list.
Used by Goods & Storage contracts for inventory batch logging.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/api/item-catalogue",
    tags=["Item Catalogue"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("ItemCatalogueRouter", log_file="logs/item_catalogue.log", level=logging.DEBUG)


class CatalogueItemCreate(BaseModel):
    name: str
    category: str
    unit: str
    description: Optional[str] = None
    is_active: bool = True


class CatalogueItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


def _require_admin(current_user: dict):
    role = current_user.get("role", "")
    if role not in ("Admin", "SuperAdmin"):
        raise HTTPException(status_code=403, detail="Only Admin or SuperAdmin can manage the item catalogue.")


@router.get("/")
async def get_catalogue_items(
    active_only: bool = False,
    current_user: dict = Depends(get_current_active_user),
):
    """Get all catalogue items. Pass active_only=true to filter inactive."""
    from backend.models.inventory_batch import ItemCatalogue
    if active_only:
        items = await ItemCatalogue.find(ItemCatalogue.is_active == True).to_list()
    else:
        items = await ItemCatalogue.find_all().to_list()
    return items


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_catalogue_item(
    payload: CatalogueItemCreate,
    current_user: dict = Depends(get_current_active_user),
):
    _require_admin(current_user)
    from backend.models.inventory_batch import ItemCatalogue
    from backend.database import get_next_uid

    existing = await ItemCatalogue.find_one(ItemCatalogue.name == payload.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Item '{payload.name}' already exists in catalogue.")

    uid = await get_next_uid("item_catalogue")
    item = ItemCatalogue(
        uid=uid,
        name=payload.name,
        category=payload.category,
        unit=payload.unit,
        description=payload.description,
        is_active=payload.is_active,
        created_by_admin_id=current_user.get("uid"),
    )
    await item.insert()
    logger.info("Catalogue item created: %s by %s", payload.name, current_user.get("sub"))
    return item


@router.put("/{item_uid}", status_code=status.HTTP_200_OK)
async def update_catalogue_item(
    item_uid: int,
    payload: CatalogueItemUpdate,
    current_user: dict = Depends(get_current_active_user),
):
    _require_admin(current_user)
    from backend.models.inventory_batch import ItemCatalogue
    from datetime import datetime

    item = await ItemCatalogue.find_one(ItemCatalogue.uid == item_uid)
    if not item:
        raise HTTPException(status_code=404, detail=f"Catalogue item {item_uid} not found.")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(item, field, value)
    item.updated_at = datetime.now()
    await item.save()
    return item


@router.delete("/{item_uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalogue_item(
    item_uid: int,
    current_user: dict = Depends(get_current_active_user),
):
    _require_admin(current_user)
    from backend.models.inventory_batch import ItemCatalogue

    item = await ItemCatalogue.find_one(ItemCatalogue.uid == item_uid)
    if not item:
        raise HTTPException(status_code=404, detail=f"Catalogue item {item_uid} not found.")
    await item.delete()
    return None
