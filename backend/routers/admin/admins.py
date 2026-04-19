# backend/routers/admins.py

import logging
import os
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, status

from backend import schemas
from backend.security import get_current_active_user, require_permission
from backend.services.admin.admin_service import AdminService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/admins",
    tags=["Administrators"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("AdminsRouter", log_file="logs/admins_router.log", level=logging.DEBUG)
service = AdminService()

ADMIN_PHOTO_DIR = os.path.join("backend", "uploads", "admin_photos")


@router.get("/", dependencies=[Depends(require_permission("admin:view_all"))])
async def get_all_admins():
    return await service.get_all_admins()


@router.get("/managers", response_model=List[schemas.AdminPublic])
async def get_all_managers(current_user: dict = Depends(get_current_active_user)):
    return await service.get_all_managers(current_user)


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_active_user)):
    return await service.get_my_profile(current_user.get("id"))


@router.put("/me")
async def update_my_profile(
    payload: schemas.AdminSelfUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.update_my_profile(current_user.get("id"), payload)


@router.put("/me/password")
async def change_my_password(
    payload: schemas.ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user),
):
    await service.change_password(
        admin_id=current_user.get("id"),
        new_password=payload.new_password,
        current_password=payload.current_password,
    )
    return {"message": "Password changed successfully"}


@router.post("/me/photo")
async def upload_my_photo(
    photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    content = await photo.read()
    return await service.upload_admin_photo(current_user.get("id"), content, ADMIN_PHOTO_DIR)


@router.post("/{admin_id}/photo", dependencies=[Depends(require_permission("admin:edit"))])
async def upload_admin_photo(
    admin_id: int,
    photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    content = await photo.read()
    return await service.upload_admin_photo(admin_id, content, ADMIN_PHOTO_DIR)


@router.get("/{admin_id}", response_model=schemas.AdminPublic, dependencies=[Depends(require_permission("admin:view_all"))])
async def get_admin_by_id(admin_id: int):
    admin = await service.get_admin_by_id(admin_id)
    return admin.model_dump(by_alias=True, mode="json")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_admin(admin_data: schemas.AdminCreate, current_user: dict = Depends(get_current_active_user)):
    created = await service.create_admin(admin_data, current_user=current_user)
    return {"status": "success", "admin_id": created.uid}


@router.put("/{admin_id}")
async def update_admin(
    admin_id: int,
    admin_update: schemas.AdminUpdate,
    current_user: dict = Depends(require_permission("admin:edit")),
):
    return await service.update_admin(admin_id, admin_update, current_user)


@router.put("/{admin_id}/password", dependencies=[Depends(require_permission("admin:edit"))])
async def update_admin_password(admin_id: int, password_data: schemas.AdminPasswordUpdate):
    await service.change_password(admin_id=admin_id, new_password=password_data.new_password)
    return {"status": "success", "message": "Password updated successfully"}


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(admin_id: int, current_user: dict = Depends(require_permission("admin:delete"))):
    await service.delete_admin(admin_id, current_user.get("id"))
    return
