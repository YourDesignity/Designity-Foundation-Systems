# backend/routers/managers.py

import logging
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import Admin, ManagerProfile, DutyAssignment
from backend.database import get_next_uid
from backend.security import get_current_active_user, get_password_hash
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/managers",
    tags=["Managers"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("ManagersRouter", log_file="logs/managers_router.log", level=logging.DEBUG)

# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class CreateManagerRequest(BaseModel):
    # Login Credentials
    email: str
    password: str

    # Required Profile Info
    full_name: str
    designation: str
    monthly_salary: float
    date_of_joining: date

    # Optional Profile Info
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

    # Site Assignments
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


# =============================================================================
# 1. CREATE MANAGER
# =============================================================================

@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def create_manager(
    payload: CreateManagerRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create a new Site Manager.
    Creates both Admin account and ManagerProfile.

    Admin only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create managers")

    # Validate email is unique
    existing_admin = await Admin.find_one(Admin.email == payload.email)
    if existing_admin:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create Admin account
    admin = Admin(
        uid=await get_next_uid("admins"),
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        designation=payload.designation,
        role="Site Manager",
        permissions=[
            'employee:view_assigned',
            'attendance:update',
            'site:view',
            'schedule:edit',
            'schedule:view_assigned'
        ],
        assigned_site_uids=payload.assigned_site_uids or [],
        is_active=True,
        has_manager_profile=True
    )
    await admin.insert()

    # Create Manager Profile
    profile = ManagerProfile(
        uid=await get_next_uid("manager_profiles"),
        admin_id=admin.uid,
        full_name=payload.full_name,
        designation=payload.designation,
        monthly_salary=payload.monthly_salary,
        allowances=payload.allowances or 0.0,
        date_of_joining=datetime.combine(payload.date_of_joining, datetime.min.time()),
        phone=payload.phone,
        address=payload.address,
        emergency_contact=payload.emergency_contact,
        emergency_phone=payload.emergency_phone,
        bank_name=payload.bank_name,
        account_number=payload.account_number,
        iban=payload.iban,
        nationality=payload.nationality,
        passport_number=payload.passport_number,
        civil_id=payload.civil_id,
        created_by_admin_id=current_user.get("id", 0)
    )
    await profile.insert()

    logger.info(f"Manager created: {admin.email} (ID: {admin.uid}) by Admin {current_user.get('sub')}")

    return {
        "message": "Manager created successfully",
        "admin_id": admin.uid,
        "profile_id": profile.uid
    }


# =============================================================================
# 2. GET ALL MANAGERS
# =============================================================================

@router.get("/profiles")
async def get_all_managers(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get list of all managers with their profiles.
    Admin only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view manager list")

    admins = await Admin.find({"role": "Site Manager", "is_active": True}).to_list()

    result = []
    for admin in admins:
        profile = await ManagerProfile.find_one(ManagerProfile.admin_id == admin.uid)

        if profile:
            result.append({
                "admin_id": admin.uid,
                "profile_id": profile.uid,
                "email": admin.email,
                "full_name": profile.full_name,
                "designation": profile.designation,
                "monthly_salary": profile.monthly_salary,
                "allowances": profile.allowances,
                "phone": profile.phone,
                "assigned_sites": admin.assigned_site_uids,
                "is_active": profile.is_active,
                "date_of_joining": profile.date_of_joining.isoformat(),
                "created_at": profile.created_at.isoformat()
            })

    logger.info(f"Manager list requested by {current_user.get('sub')}: {len(result)} managers")
    return result


# =============================================================================
# 3. GET MANAGER DETAILS
# =============================================================================

@router.get("/profiles/{manager_id}")
async def get_manager_profile(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get detailed profile of a specific manager.
    Admin only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can view manager details")

    admin = await Admin.find_one(Admin.uid == manager_id)
    if not admin or admin.role != "Site Manager":
        raise HTTPException(status_code=404, detail="Manager not found")

    profile = await ManagerProfile.find_one(ManagerProfile.admin_id == manager_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Manager profile not found")

    return {
        "admin_id": admin.uid,
        "profile_id": profile.uid,
        "email": admin.email,
        "full_name": profile.full_name,
        "designation": profile.designation,
        "monthly_salary": profile.monthly_salary,
        "allowances": profile.allowances,
        "phone": profile.phone,
        "address": profile.address,
        "emergency_contact": profile.emergency_contact,
        "emergency_phone": profile.emergency_phone,
        "bank_name": profile.bank_name,
        "account_number": profile.account_number,
        "iban": profile.iban,
        "nationality": profile.nationality,
        "passport_number": profile.passport_number,
        "civil_id": profile.civil_id,
        "assigned_site_uids": admin.assigned_site_uids,
        "is_active": profile.is_active,
        "date_of_joining": profile.date_of_joining.isoformat(),
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat()
    }


# =============================================================================
# 4. UPDATE MANAGER PROFILE
# =============================================================================

@router.put("/profiles/{manager_id}")
async def update_manager_profile(
    manager_id: int,
    payload: UpdateManagerProfileRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update manager profile information.
    Admin only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update manager profiles")

    profile = await ManagerProfile.find_one(ManagerProfile.admin_id == manager_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Manager profile not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.now()
    await profile.save()

    # Also update Admin full_name and designation if changed
    if "full_name" in update_data or "designation" in update_data:
        admin = await Admin.find_one(Admin.uid == manager_id)
        if admin:
            if "full_name" in update_data:
                admin.full_name = update_data["full_name"]
            if "designation" in update_data:
                admin.designation = update_data["designation"]
            await admin.save()

    logger.info(f"Manager {manager_id} profile updated by {current_user.get('sub')}")
    return {"message": "Manager profile updated successfully"}


# =============================================================================
# 5. UPDATE MANAGER CREDENTIALS
# =============================================================================

@router.put("/profiles/{manager_id}/credentials")
async def update_manager_credentials(
    manager_id: int,
    payload: UpdateCredentialsRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update manager email and/or password.
    Admin only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update credentials")

    admin = await Admin.find_one(Admin.uid == manager_id)
    if not admin or admin.role != "Site Manager":
        raise HTTPException(status_code=404, detail="Manager not found")

    if payload.email:
        existing = await Admin.find_one({"email": payload.email, "uid": {"$ne": manager_id}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        admin.email = payload.email

    if payload.password:
        admin.hashed_password = get_password_hash(payload.password)

    await admin.save()

    logger.info(f"Manager {manager_id} credentials updated by {current_user.get('sub')}")
    return {"message": "Credentials updated successfully"}


# =============================================================================
# 6. UPDATE MANAGER SITE ASSIGNMENTS
# =============================================================================

@router.put("/profiles/{manager_id}/sites")
async def update_manager_sites(
    manager_id: int,
    payload: UpdateSitesRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update manager's assigned sites.
    Admin only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can update site assignments")

    admin = await Admin.find_one(Admin.uid == manager_id)
    if not admin or admin.role != "Site Manager":
        raise HTTPException(status_code=404, detail="Manager not found")

    admin.assigned_site_uids = payload.site_uids
    await admin.save()

    logger.info(f"Manager {manager_id} sites updated to {payload.site_uids} by {current_user.get('sub')}")
    return {"message": "Site assignments updated successfully"}


# =============================================================================
# 7. DELETE MANAGER
# =============================================================================

@router.delete("/profiles/{manager_id}")
async def delete_manager(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Permanently delete a manager.
    Deletes Admin account, ManagerProfile, and related duty assignment records.

    Admin only. USE WITH CAUTION.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete managers")

    admin = await Admin.find_one(Admin.uid == manager_id)
    if not admin or admin.role != "Site Manager":
        raise HTTPException(status_code=404, detail="Manager not found")

    profile = await ManagerProfile.find_one(ManagerProfile.admin_id == manager_id)

    if profile:
        await profile.delete()

    await admin.delete()

    # Remove from duty assignments (bulk delete)
    await DutyAssignment.find(DutyAssignment.manager_id == manager_id).delete()

    logger.warning(f"Manager {manager_id} ({admin.email}) DELETED by {current_user.get('sub')}")
    return {"message": "Manager deleted successfully"}
