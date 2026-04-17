# backend/routers/managers.py

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.security import get_current_active_user
from backend.services.admin.manager_service import ManagerService
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/managers",
    tags=["Managers"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("ManagersRouter", log_file="logs/managers_router.log", level=logging.DEBUG)
service = ManagerService()


class CreateManagerRequest(BaseModel):
    email: str
    password: str
    full_name: str
    designation: str
    monthly_salary: float
    date_of_joining: date
    allowances: Optional[float] = 0.0
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    civil_id: Optional[str] = None
    assigned_site_uids: Optional[List[int]] = []


class UpdateManagerProfileRequest(BaseModel):
    full_name: Optional[str] = None
    designation: Optional[str] = None
    monthly_salary: Optional[float] = None
    allowances: Optional[float] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    civil_id: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateCredentialsRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


class UpdateSitesRequest(BaseModel):
    site_uids: List[int]


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def create_manager(
    payload: CreateManagerRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.create_manager(payload, current_user)


@router.get("/profiles")
async def get_all_managers(current_user: dict = Depends(get_current_active_user)):
    return await service.get_all_managers(current_user)


@router.get("/profiles/{manager_id}")
async def get_manager_profile(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.get_manager_profile(manager_id, current_user)


@router.put("/profiles/{manager_id}")
async def update_manager_profile(
    manager_id: int,
    payload: UpdateManagerProfileRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.update_manager_profile(manager_id, payload, current_user)


@router.put("/profiles/{manager_id}/credentials")
async def update_manager_credentials(
    manager_id: int,
    payload: UpdateCredentialsRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.update_manager_credentials(manager_id, payload, current_user)


@router.put("/profiles/{manager_id}/sites")
async def update_manager_sites(
    manager_id: int,
    payload: UpdateSitesRequest,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.update_manager_sites(manager_id, payload, current_user)


@router.delete("/profiles/{manager_id}")
async def delete_manager(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    return await service.delete_manager(manager_id, current_user)
