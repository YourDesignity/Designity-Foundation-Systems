# backend/routers/admins.py

import logging
import json
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

# --- Imports ---
from backend.models import Admin
from backend import schemas
from backend.security import get_current_active_user, get_password_hash, verify_password, require_permission, PRIVILEGED_ROLES
from backend.database import get_next_uid
from backend.utils.logger import setup_logger 

# --- NEW: Import the Dynamic Config Loader ---
from backend.core.config_loader import RoleConfig

router = APIRouter(
    prefix="/admins",
    tags=["Administrators"],
    dependencies=[Depends(get_current_active_user)]
)

# Initialize Logger
logger = setup_logger("AdminsRouter", log_file="logs/admins_router.log", level=logging.DEBUG)

# =============================================================================
# 1. READ ALL ADMINS
# =============================================================================

@router.get("/", dependencies=[Depends(require_permission("admin:view_all"))])
async def get_all_admins():
    logger.info("ENDPOINT START: GET /admins")
    
    try:
        admins = await Admin.find_all().to_list()
        
        results = []
        for admin in admins:
            # 1. Dynamic Role Lookup
            # We use the config loader to find the ID associated with the string in DB
            role_config = RoleConfig.get_role_by_name(admin.role)
            role_id = role_config["legacy_id"] if role_config else 0

            # 2. Deep Logging (Pydantic v2 style)
            # mode='json' automatically handles ObjectId and Datetime conversion
            debug_dump = admin.model_dump(mode='json')
            logger.debug(f"RAW ITEM: {json.dumps(debug_dump, indent=None)}") 

            results.append({
                "id": admin.uid,
                "email": admin.email,
                "full_name": admin.full_name,
                "designation": admin.designation,
                "is_active": admin.is_active,
                "created_at": admin.created_at,
                "profile_photo": admin.profile_photo,
                "role": {
                    "id": role_id,
                    "name": admin.role,
                    "description": "Managed by Config"
                }
            })
        
        logger.info(f"RESPONSE: Returning {len(results)} admins.")
        # Log the full response for deep debugging
        logger.debug(f"RESPONSE PAYLOAD:\n{json.dumps(results, indent=2, default=str)}")
        return results

    except Exception as e:
        logger.critical(f"CRITICAL ERROR in GET /admins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# =============================================================================
# 2. READ MANAGERS (For Dropdowns)
# =============================================================================

@router.get("/managers", response_model=List[schemas.AdminPublic])
async def get_all_managers(current_user: dict = Depends(get_current_active_user)):
    """
    Returns only admins with role 'Site Manager'.
    """
    logger.info("ENDPOINT START: GET /admins/managers")
    
    user_role = current_user.get("role")
    # You might want to move these allowed roles to config in the future too
    if user_role not in ["SuperAdmin", "Admin", "Site Manager"]:
        logger.warning(f"ACCESS DENIED: Role '{user_role}' tried to fetch managers.")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # Fetching based on the DB name string. 
        # Note: In a fully dynamic system, you might fetch the name from Config first.
        managers = await Admin.find(Admin.role == "Site Manager", Admin.is_active == True).to_list()
        
        # Log the raw results
        raw_dump = [m.model_dump(mode='json') for m in managers]
        logger.debug(f"DB FETCH (Managers):\n{json.dumps(raw_dump, indent=2)}")
        
        # Serialize to dicts so Pydantic validation_alias ("uid" → "id") works correctly
        return [m.model_dump(mode='json') for m in managers]

    except Exception as e:
        logger.error(f"ERROR in GET /managers: {e}")
        raise

# =============================================================================
# 3. READ SINGLE ADMIN
# =============================================================================

# ── Self-service /me endpoints ────────────────────────────────────────────────
# IMPORTANT: these static routes MUST appear before /{admin_id} so FastAPI
# does not treat the literal string "me" as an integer admin_id.
# =============================================================================

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_active_user)):
    """Return the profile of the currently authenticated admin."""
    admin = await Admin.find_one(Admin.uid == current_user.get("id"))
    if not admin:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "id": admin.uid,
        "email": admin.email,
        "full_name": admin.full_name,
        "designation": admin.designation,
        "role": admin.role,
        "phone": admin.phone,
        "profile_photo": admin.profile_photo,
        "created_at": admin.created_at.isoformat() if admin.created_at else None,
    }


@router.put("/me")
async def update_my_profile(
    payload: schemas.AdminSelfUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Allow the authenticated admin to update their own profile fields."""
    admin = await Admin.find_one(Admin.uid == current_user.get("id"))
    if not admin:
        raise HTTPException(status_code=404, detail="Profile not found")

    if payload.full_name is not None:
        admin.full_name = payload.full_name
    if payload.designation is not None:
        admin.designation = payload.designation
    if payload.phone is not None:
        admin.phone = payload.phone

    await admin.save()
    return {"message": "Profile updated successfully"}


@router.put("/me/password")
async def change_my_password(
    payload: schemas.ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Allow the authenticated admin to change their own password."""
    admin = await Admin.find_one(Admin.uid == current_user.get("id"))
    if not admin:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not verify_password(payload.current_password, admin.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    admin.hashed_password = get_password_hash(payload.new_password)
    await admin.save()
    return {"message": "Password changed successfully"}


ADMIN_PHOTO_DIR = os.path.join("backend", "uploads", "admin_photos")
os.makedirs(ADMIN_PHOTO_DIR, exist_ok=True)


@router.post("/me/photo")
async def upload_my_photo(
    photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Upload a profile photo for the authenticated admin."""
    content = await photo.read()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5 MB")

    # Validate via magic bytes and derive extension from actual content (not user-provided)
    is_jpeg = len(content) >= 3 and content[:3] == b"\xff\xd8\xff"
    is_png = len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n"
    if not (is_jpeg or is_png):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed")

    # Extension is determined by magic bytes, not user-provided content-type
    ext = "png" if is_png else "jpg"
    admin_id = current_user.get("id")
    filename = f"admin_{admin_id}.{ext}"
    file_path = os.path.join(ADMIN_PHOTO_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    admin = await Admin.find_one(Admin.uid == admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Profile not found")

    admin.profile_photo = f"/uploads/admin_photos/{filename}"
    await admin.save()

    return {"message": "Photo uploaded successfully", "photo_url": admin.profile_photo}


# ── Upload photo for a specific admin by ID ────────────────────────────────────

@router.post("/{admin_id}/photo", dependencies=[Depends(require_permission("admin:edit"))])
async def upload_admin_photo(
    admin_id: int,
    photo: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Upload a profile photo for a specific admin. Requires the 'admin:edit' permission."""
    content = await photo.read()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5 MB")

    is_jpeg = len(content) >= 3 and content[:3] == b"\xff\xd8\xff"
    is_png = len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n"
    if not (is_jpeg or is_png):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are allowed")

    ext = "png" if is_png else "jpg"
    # admin_id is validated as int by FastAPI; use int() to make the path safe
    safe_admin_id = int(admin_id)
    filename = f"admin_{safe_admin_id}.{ext}"
    file_path = os.path.join(ADMIN_PHOTO_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    admin = await Admin.find_one(Admin.uid == safe_admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    admin.profile_photo = f"/uploads/admin_photos/{filename}"
    await admin.save()

    return {"message": "Photo uploaded successfully", "photo_url": admin.profile_photo}


# ── Single admin by ID ─────────────────────────────────────────────────────────

@router.get("/{admin_id}", response_model=schemas.AdminPublic, dependencies=[Depends(require_permission("admin:view_all"))])
async def get_admin_by_id(admin_id: int):
    logger.info(f"ENDPOINT START: GET /admins/{admin_id}")

    admin = await Admin.find_one(Admin.uid == admin_id)
    if not admin:
        logger.warning(f"LOOKUP FAILED: Admin {admin_id} not found.")
        raise HTTPException(status_code=404, detail="Admin not found")
    
    output_dict = admin.model_dump(by_alias=True, mode='json')
    logger.debug(f"OUTPUT DATA:\n{json.dumps(output_dict, indent=2)}")
    
    return output_dict

# =============================================================================
# 4. CREATE ADMIN
# =============================================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_admin(admin_data: schemas.AdminCreate, current_user: dict = Depends(get_current_active_user)):
    logger.info(f"ENDPOINT START: POST /admins - Email: {admin_data.email}")

    # 1. Log Input (Sanitized)
    input_dump = admin_data.model_dump(mode='json')
    if 'password' in input_dump: input_dump['password'] = '******'
    logger.debug(f"INPUT PAYLOAD:\n{json.dumps(input_dump, indent=2)}")

    # 2. DYNAMIC ROLE RESOLUTION
    target_role_config = RoleConfig.get_role_by_id(admin_data.role_id)
    
    if not target_role_config:
        logger.error(f"Invalid Role ID: {admin_data.role_id}")
        raise HTTPException(status_code=400, detail="Invalid Role ID")

    target_role_name = target_role_config["db_name"]
    
    # 3. DYNAMIC PERMISSIONS
    default_perms = target_role_config["permissions"]
    logger.debug(f"CONFIG LOADED: Mapped ID {admin_data.role_id} -> '{target_role_name}'. Assigning {len(default_perms)} perms.")

    # 4. Security Check
    # SuperAdmin and Admin bypass permission checks
    user_role = current_user.get("role")
    if user_role not in PRIVILEGED_ROLES:
        required_perm = 'admin:create:admin'
        if target_role_name == 'Site Manager':
            required_perm = 'admin:create:manager'

        user_perms = current_user.get("perms", [])
        if required_perm not in user_perms:
            logger.critical(f"SECURITY: User {current_user.get('email')} missing perm '{required_perm}'")
            raise HTTPException(status_code=403, detail=f"Missing permission: {required_perm}")

    if await Admin.find_one(Admin.email == admin_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # 5. Create Object
    new_uid = await get_next_uid("admins")
    hashed_password = get_password_hash(admin_data.password)

    new_admin = Admin(
        uid=new_uid,
        email=admin_data.email,
        hashed_password=hashed_password,
        full_name=admin_data.full_name,
        designation=admin_data.designation,
        role=target_role_name,
        permissions=default_perms, # Loaded dynamically
        assigned_site_uids=[]
    )

    await new_admin.insert()
    
    # Log Result
    log_payload = new_admin.model_dump(mode='json', exclude={'hashed_password'})
    logger.info(f"SUCCESS CREATION:\n{json.dumps(log_payload, indent=2)}")

    return {"status": "success", "admin_id": new_uid}

# =============================================================================
# 5. UPDATE ADMIN
# =============================================================================

@router.put("/{admin_id}")
async def update_admin(admin_id: int, admin_update: schemas.AdminUpdate, current_user: dict = Depends(require_permission("admin:edit"))):
    logger.info(f"ENDPOINT START: PUT /admins/{admin_id}")

    admin = await Admin.find_one(Admin.uid == admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # Security check: Only SuperAdmin can edit SuperAdmin accounts
    if admin.role and admin.role.lower() == "superadmin":
        if current_user.get("role") != "SuperAdmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SuperAdmins can edit SuperAdmin accounts"
            )

    # Standard updates
    if admin_update.full_name: admin.full_name = admin_update.full_name
    if admin_update.designation: admin.designation = admin_update.designation
    if admin_update.is_active is not None: admin.is_active = admin_update.is_active
    
    # DYNAMIC ROLE UPDATE
    if admin_update.role_id:
        new_role_config = RoleConfig.get_role_by_id(admin_update.role_id)
        if new_role_config:
            new_role_name = new_role_config["db_name"]
            logger.warning(f"ROLE CHANGE: '{admin.role}' -> '{new_role_name}'")
            
            admin.role = new_role_name
            # Automatically pull new permissions from JSON
            admin.permissions = new_role_config["permissions"] 
        else:
            logger.error(f"Invalid Role ID provided: {admin_update.role_id}")

    await admin.save()
    logger.info(f"Admin {admin_id} updated successfully.")
    return {"status": "success"}

# =============================================================================
# 6. UPDATE ADMIN PASSWORD
# =============================================================================

@router.put("/{admin_id}/password", dependencies=[Depends(require_permission("admin:edit"))])
async def update_admin_password(admin_id: int, password_data: schemas.AdminPasswordUpdate):
    logger.info(f"ENDPOINT START: PUT /admins/{admin_id}/password")

    admin = await Admin.find_one(Admin.uid == admin_id)
    if not admin:
        logger.warning(f"LOOKUP FAILED: Admin {admin_id} not found.")
        raise HTTPException(status_code=404, detail="Admin not found")

    admin.hashed_password = get_password_hash(password_data.new_password)
    await admin.save()
    logger.info(f"Password updated for admin {admin_id}.")
    return {"status": "success", "message": "Password updated successfully"}

# =============================================================================
# 7. DELETE ADMIN
# =============================================================================

@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(admin_id: int, current_user: dict = Depends(require_permission("admin:delete"))):
    logger.warning(f"ENDPOINT START: DELETE /admins/{admin_id}")

    admin = await Admin.find_one(Admin.uid == admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # Safety check: Cannot delete yourself
    if admin_id == current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete your own account"
        )
        
    # AUDIT SNAPSHOT
    audit_dump = admin.model_dump(mode='json', exclude={'hashed_password'})
    logger.warning(f"AUDIT SNAPSHOT - DELETING USER:\n{json.dumps(audit_dump, indent=2)}")
    
    await admin.delete()
    logger.info(f"SUCCESS: Admin {admin_id} deleted.")
    return




























# # backend/routers/admins.py

# import logging
# import json
# from datetime import datetime, date
# from typing import List, Dict, Any
# from fastapi import APIRouter, Depends, HTTPException, status
# from beanie import PydanticObjectId
# from bson import ObjectId

# # --- Imports from your project ---
# from backend.database import get_next_uid
# from backend.models import Admin, Site
# from backend import schemas
# from backend.security import get_current_active_user, get_password_hash, require_permission
# from backend.utils.logger import setup_logger 

# router = APIRouter(
#     prefix="/admins",
#     tags=["Administrators"],
#     dependencies=[Depends(get_current_active_user)]
# )

# # --- Initialize Logger ---
# logger = setup_logger("AdminsRouter", log_file="logs/admins_router.log", level=logging.DEBUG)

# # --- HELPER: Pretty JSON Serializer ---
# # This handles Datetime and ObjectId so json.dumps doesn't crash
# def pretty_json(data: Any) -> str:
#     def default_serializer(obj):
#         if isinstance(obj, (datetime, date)):
#             return obj.isoformat()  # Convert date to "2025-12-26T19:56:21..."
#         if isinstance(obj, (ObjectId, PydanticObjectId)):
#             return str(obj)         # Convert ObjectId('...') to string
#         return str(obj)             # Fallback for anything else
    
#     # indent=2 makes it vertical and readable
#     return json.dumps(data, default=default_serializer, indent=2)

# # --- COMPATIBILITY LAYER ---
# ROLE_ID_MAP = {
#     1: "SuperAdmin",
#     2: "Admin",
#     3: "Site Manager"
# }
# ROLE_NAME_TO_ID = {v: k for k, v in ROLE_ID_MAP.items()}

# def get_default_perms_for_role(role_name: str) -> List[str]:
#     # (Kept brief for readability, logic unchanged)
#     if role_name == "SuperAdmin": return ["all"]
#     if role_name == "Site Manager": 
#         return ['employee:view_assigned', 'attendance:update', 'site:view', 'schedule:edit', 'schedule:view_assigned']
#     return ['employee:view_all', 'employee:create', 'employee:edit', 'employee:delete', 'attendance:update', 'payslip:generate', 'payslip:view_all', 'admin:view_all', 'admin:create:manager', 'admin:edit', 'admin:delete', 'site:create', 'site:view', 'site:edit', 'site:delete', 'schedule:edit', 'schedule:view_assigned']

# # =============================================================================
# # 1. READ ALL ADMINS
# # =============================================================================

# @router.get("/", dependencies=[Depends(require_permission("admin:view_all"))])
# async def get_all_admins():
#     logger.info("ENDPOINT START: GET /admins")
    
#     try:
#         admins = await Admin.find_all().to_list()
#         logger.debug(f"DB FETCH: Retrieved {len(admins)} raw documents.")
        
#         results = []
#         for index, admin in enumerate(admins):
#             # 1. RAW DATA (Pretty Printed)
#             raw_doc = admin.model_dump()
#             logger.debug(f"RAW DATA [Item {index}]:\n{pretty_json(raw_doc)}")

#             # 2. TRANSFORM DATA
#             role_id = ROLE_NAME_TO_ID.get(admin.role, 0)
            
#             response_structure = {
#                 "id": admin.uid,
#                 "email": admin.email,
#                 "full_name": admin.full_name,
#                 "designation": admin.designation,
#                 "is_active": admin.is_active,
#                 "created_at": admin.created_at,
#                 "role": {
#                     "id": role_id,
#                     "name": admin.role,
#                     "description": "Managed by Mongo"
#                 }
#             }

#             # 3. TRANSFORMED DATA (Pretty Printed)
#             logger.debug(f"TRANSFORMED DATA [Item {index}]:\n{pretty_json(response_structure)}")
#             results.append(response_structure)
        
#         logger.info(f"RESPONSE PREP: Sending list of {len(results)} items.")
#         return results

#     except Exception as e:
#         logger.critical(f"EXCEPTION in GET /admins: {str(e)}", exc_info=True)
#         raise

# # =============================================================================
# # 2. READ MANAGERS
# # =============================================================================

# @router.get("/managers", response_model=List[schemas.AdminPublic])
# async def get_all_managers(current_user: dict = Depends(get_current_active_user)):
#     logger.info("ENDPOINT START: GET /admins/managers")
    
#     user_role = current_user.get("role")
#     if user_role not in ["SuperAdmin", "Admin"]:
#         logger.warning(f"ACCESS DENIED: Role '{user_role}' forbidden.")
#         raise HTTPException(status_code=403, detail="Forbidden")

#     try:
#         managers = await Admin.find(Admin.role == "Site Manager", Admin.is_active == True).to_list()
        
#         # Log the entire list structure properly
#         raw_list = [m.model_dump() for m in managers]
#         logger.debug(f"DB FETCH (Managers Found):\n{pretty_json(raw_list)}")
        
#         response_data = []
#         for mgr in managers:
#             response_data.append({
#                 "id": mgr.uid, 
#                 "email": mgr.email, 
#                 "full_name": mgr.full_name, 
#                 "designation": mgr.designation
#             })

#         logger.debug(f"OUTPUT DATA (Dropdown Format):\n{pretty_json(response_data)}")
#         return response_data

#     except Exception as e:
#         logger.error(f"EXCEPTION: {e}")
#         raise

# # =============================================================================
# # 3. READ SINGLE ADMIN
# # =============================================================================

# @router.get("/{admin_id}", response_model=schemas.AdminPublic, dependencies=[Depends(require_permission("admin:view_all"))])
# async def get_admin_by_id(admin_id: int):
#     logger.info(f"ENDPOINT START: GET /admins/{admin_id}")

#     admin = await Admin.find_one(Admin.uid == admin_id)
#     if not admin:
#         logger.warning(f"LOOKUP FAILED: Admin {admin_id} not found.")
#         raise HTTPException(status_code=404, detail="Admin not found")
    
#     output_dict = admin.model_dump(by_alias=True)
#     logger.debug(f"OUTPUT DATA (Single Record):\n{pretty_json(output_dict)}")
    
#     return output_dict

# # =============================================================================
# # 4. CREATE ADMIN
# # =============================================================================

# @router.post("/", status_code=status.HTTP_201_CREATED)
# async def create_admin(admin_data: schemas.AdminCreate, current_user: dict = Depends(get_current_active_user)):
#     logger.info("ENDPOINT START: POST /admins")
    
#     # 1. Log Incoming JSON (Sanitized)
#     raw_input_dict = admin_data.model_dump()
#     log_safe_input = raw_input_dict.copy()
#     if 'password' in log_safe_input:
#         log_safe_input['password'] = '******'
    
#     logger.debug(f"INPUT PAYLOAD:\n{pretty_json(log_safe_input)}")

#     # 2. Logic Tracing
#     target_role_name = ROLE_ID_MAP.get(admin_data.role_id)
    
#     if not target_role_name:
#         logger.error(f"VALIDATION ERROR: Invalid Role ID {admin_data.role_id}")
#         raise HTTPException(status_code=400, detail="Invalid Role ID")
        
#     required_perm = 'admin:create:admin'
#     if target_role_name == 'Site Manager':
#         required_perm = 'admin:create:manager'
        
#     user_perms = current_user.get("perms", [])
#     if required_perm not in user_perms:
#         logger.critical(f"SECURITY: Missing permission '{required_perm}'")
#         raise HTTPException(status_code=403, detail=f"Missing permission: {required_perm}")

#     if await Admin.find_one(Admin.email == admin_data.email):
#         logger.warning(f"VALIDATION ERROR: Email '{admin_data.email}' collision.")
#         raise HTTPException(status_code=400, detail="Email already registered")

#     # 3. Create & Log DB Object
#     hashed_password = get_password_hash(admin_data.password)
#     new_uid = await get_next_uid("admins")
#     default_perms = get_default_perms_for_role(target_role_name)

#     new_admin = Admin(
#         uid=new_uid,
#         email=admin_data.email,
#         hashed_password=hashed_password,
#         full_name=admin_data.full_name,
#         designation=admin_data.designation,
#         role=target_role_name,
#         permissions=default_perms,
#         assigned_site_uids=[]
#     )
    
#     doc_structure = new_admin.model_dump(exclude={'hashed_password'})
#     logger.debug(f"DB INSERT PREP (Document):\n{pretty_json(doc_structure)}")

#     await new_admin.insert()
    
#     response_payload = {"status": "success", "admin_id": new_uid, "email": admin_data.email}
#     logger.info(f"SUCCESS. Returning:\n{pretty_json(response_payload)}")
#     return response_payload

# # =============================================================================
# # 5. UPDATE ADMIN
# # =============================================================================

# @router.put("/{admin_id}", dependencies=[Depends(require_permission("admin:edit"))])
# async def update_admin(admin_id: int, admin_update: schemas.AdminUpdate):
#     logger.info(f"ENDPOINT START: PUT /admins/{admin_id}")

#     # Log changes only
#     raw_changes = admin_update.model_dump(exclude_unset=True)
#     logger.debug(f"INPUT PAYLOAD (Changes):\n{pretty_json(raw_changes)}")

#     admin = await Admin.find_one(Admin.uid == admin_id)
#     if not admin:
#         raise HTTPException(status_code=404, detail="Admin not found")

#     if admin_update.full_name: admin.full_name = admin_update.full_name
#     if admin_update.designation: admin.designation = admin_update.designation
#     if admin_update.is_active is not None: admin.is_active = admin_update.is_active
    
#     if admin_update.role_id:
#         new_role = ROLE_ID_MAP.get(admin_update.role_id)
#         if new_role:
#             logger.info(f"LOGIC: Role change '{admin.role}' -> '{new_role}'")
#             admin.role = new_role
#             admin.permissions = get_default_perms_for_role(new_role)

#     await admin.save()
#     logger.info("SUCCESS: Admin updated.")
#     return {"status": "success"}

# # =============================================================================
# # 6. DELETE ADMIN
# # =============================================================================

# @router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("admin:delete"))])
# async def delete_admin(admin_id: int):
#     logger.warning(f"ENDPOINT START: DELETE /admins/{admin_id}")

#     admin = await Admin.find_one(Admin.uid == admin_id)
#     if not admin:
#         raise HTTPException(status_code=404, detail="Admin not found")
        
#     audit_snapshot = admin.model_dump()
#     logger.warning(f"AUDIT SNAPSHOT (Deleting):\n{pretty_json(audit_snapshot)}")
    
#     await admin.delete()
#     return




























# # backend/routers/admins.py

# from typing import List, Dict, Any
# from fastapi import APIRouter, Depends, HTTPException, status
# from beanie import PydanticObjectId

# from backend.database import get_next_uid
# from backend.models import Admin, Site
# from backend import schemas
# from backend.security import get_current_active_user, get_password_hash, require_permission

# router = APIRouter(
#     prefix="/admins",
#     tags=["Administrators"],
#     dependencies=[Depends(get_current_active_user)]
# )

# # --- COMPATIBILITY LAYER ---
# # Maps Frontend Integers to Backend Strings and back.
# # This ensures we don't need to change the Frontend dropdowns.
# ROLE_ID_MAP = {
#     1: "SuperAdmin",
#     2: "Admin",
#     3: "Site Manager"
# }
# # Reverse map for responses
# ROLE_NAME_TO_ID = {v: k for k, v in ROLE_ID_MAP.items()}

# # --- HELPER: Get Permissions based on Role ---
# # (Ideally this mirrors seed_mongo.py logic)
# def get_default_perms_for_role(role_name: str) -> List[str]:
#     # Simple defaults. In a real app, you might query a config.
#     if role_name == "SuperAdmin": return ["all"] # Logic handled in specific checks usually
#     if role_name == "Site Manager": 
#         return ['employee:view_assigned', 'attendance:update', 'site:view', 'schedule:edit', 'schedule:view_assigned']
#     return ['employee:view_all', 'employee:create', 'employee:edit', 'employee:delete', 'attendance:update', 'payslip:generate', 'payslip:view_all', 'admin:view_all', 'admin:create:manager', 'admin:edit', 'admin:delete', 'site:create', 'site:view', 'site:edit', 'site:delete', 'schedule:edit', 'schedule:view_assigned']

# # =============================================================================
# # 1. READ ALL ADMINS
# # =============================================================================

# @router.get("/", dependencies=[Depends(require_permission("admin:view_all"))])
# async def get_all_admins():
#     """
#     Fetches all admins.
#     Constructs a response that mimics the old SQL JOIN structure so the frontend
#     table displays the Role Name correctly.
#     """
#     admins = await Admin.find_all().to_list()
    
#     results = []
#     for admin in admins:
#         # Reconstruct the 'role' object the frontend expects
#         role_id = ROLE_NAME_TO_ID.get(admin.role, 0)
        
#         results.append({
#             "id": admin.uid,
#             "email": admin.email,
#             "full_name": admin.full_name,
#             "designation": admin.designation,
#             "is_active": admin.is_active,
#             "created_at": admin.created_at,
#             # Frontend expects a nested object for role to display 'name'
#             "role": {
#                 "id": role_id,
#                 "name": admin.role,
#                 "description": "Managed by Mongo"
#             }
#         })
#     return results

# # =============================================================================
# # 2. READ MANAGERS (For Dropdowns)
# # =============================================================================

# @router.get("/managers", response_model=List[schemas.AdminPublic])
# async def get_all_managers(current_user: dict = Depends(get_current_active_user)):
#     """
#     Returns only admins with role 'Site Manager'.
#     Used when assigning a manager to a Site.
#     """
#     user_role = current_user.get("role")
#     if user_role not in ["SuperAdmin", "Admin"]:
#         raise HTTPException(status_code=403, detail="Forbidden")

#     # Mongo Query: Simple filter
#     managers = await Admin.find(Admin.role == "Site Manager", Admin.is_active == True).to_list()
    
#     # Map UID to ID for Pydantic
#     return [
#         {
#             "id": mgr.uid, 
#             "email": mgr.email, 
#             "full_name": mgr.full_name, 
#             "designation": mgr.designation
#         } 
#         for mgr in managers
#     ]

# # =============================================================================
# # 3. READ SINGLE ADMIN
# # =============================================================================

# @router.get("/{admin_id}", response_model=schemas.AdminPublic, dependencies=[Depends(require_permission("admin:view_all"))])
# async def get_admin_by_id(admin_id: int):
#     admin = await Admin.find_one(Admin.uid == admin_id)
#     if not admin:
#         raise HTTPException(status_code=404, detail="Admin not found")
    
#     # Pydantic alias handling usually takes care of uid -> id, but explicit dict helps debugging
#     return admin.model_dump(by_alias=True)

# # =============================================================================
# # 4. CREATE ADMIN
# # =============================================================================

# @router.post("/", status_code=status.HTTP_201_CREATED)
# async def create_admin(admin_data: schemas.AdminCreate, current_user: dict = Depends(get_current_active_user)):
#     """
#     Creates a new Admin/Manager.
#     Translates role_id (int) -> role (str).
#     """
#     # 1. Check Permissions
#     required_perm = 'admin:create:admin'
#     target_role_name = ROLE_ID_MAP.get(admin_data.role_id)
    
#     if not target_role_name:
#         raise HTTPException(status_code=400, detail="Invalid Role ID")
        
#     if target_role_name == 'Site Manager':
#         required_perm = 'admin:create:manager'
        
#     user_perms = current_user.get("perms", [])
#     if required_perm not in user_perms:
#         raise HTTPException(status_code=403, detail=f"Missing permission: {required_perm}")

#     # 2. Check for Duplicate Email
#     existing_user = await Admin.find_one(Admin.email == admin_data.email)
#     if existing_user:
#         raise HTTPException(status_code=400, detail="Email already registered")

#     # 3. Prepare Data
#     hashed_password = get_password_hash(admin_data.password)
#     new_uid = await get_next_uid("admins")
#     default_perms = get_default_perms_for_role(target_role_name)

#     # 4. Insert into Mongo
#     new_admin = Admin(
#         uid=new_uid,
#         email=admin_data.email,
#         hashed_password=hashed_password,
#         full_name=admin_data.full_name,
#         designation=admin_data.designation,
#         role=target_role_name,
#         permissions=default_perms,
#         assigned_site_uids=[]
#     )
    
#     await new_admin.insert()
    
#     return {"status": "success", "admin_id": new_uid, "email": admin_data.email}

# # =============================================================================
# # 5. UPDATE ADMIN
# # =============================================================================

# @router.put("/{admin_id}", dependencies=[Depends(require_permission("admin:edit"))])
# async def update_admin(admin_id: int, admin_update: schemas.AdminUpdate):
#     """
#     Updates details. If role_id is provided, translates it.
#     """
#     admin = await Admin.find_one(Admin.uid == admin_id)
#     if not admin:
#         raise HTTPException(status_code=404, detail="Admin not found")

#     if admin_update.full_name:
#         admin.full_name = admin_update.full_name
#     if admin_update.designation:
#         admin.designation = admin_update.designation
#     if admin_update.is_active is not None:
#         admin.is_active = admin_update.is_active
    
#     # Handle Role Change
#     if admin_update.role_id:
#         new_role = ROLE_ID_MAP.get(admin_update.role_id)
#         if new_role:
#             admin.role = new_role
#             # In a full app, you'd update perms here too
#             admin.permissions = get_default_perms_for_role(new_role)

#     await admin.save()
#     return {"status": "success"}

# # =============================================================================
# # 6. DELETE ADMIN
# # =============================================================================

# @router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("admin:delete"))])
# async def delete_admin(admin_id: int):
#     admin = await Admin.find_one(Admin.uid == admin_id)
#     if not admin:
#         raise HTTPException(status_code=404, detail="Admin not found")
        
#     await admin.delete()
#     return