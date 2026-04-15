import json
import os
import pathlib
import shutil
import logging
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Query, Request
from fastapi.responses import FileResponse

# --- Imports ---
from backend import schemas
from backend.models import Employee, Admin
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger 

# WebSocket Manager
try:
    from backend.websocket_manager import manager
except ImportError:
    from backend.websocket_manager import manager 

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
    dependencies=[Depends(get_current_active_user)]
)

# Separate router for the download endpoint (no router-level auth dependency,
# auth is handled manually inside the endpoint to support token as query param)
download_router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)

logger = setup_logger("EmployeesRouter", log_file="logs/employees_router.log", level=logging.DEBUG)

UPLOAD_DIRECTORY = os.path.join("backend", "uploads")
PHOTO_DIR = os.path.join(UPLOAD_DIRECTORY, "photos")
DOCUMENT_DIR = os.path.join(UPLOAD_DIRECTORY, "documents")

# Ensure upload directories exist
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(DOCUMENT_DIR, exist_ok=True)

# --- Helper: Save Uploaded Files ---
def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    try:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        logger.debug(f"File Saved: {destination}")
    except Exception as e:
        logger.error(f"File Save Error: {e}")
        raise HTTPException(status_code=500, detail="Could not save file.")
    finally:
        upload_file.file.close()
    return destination

# --- Helper: Dual Storage Save ---
async def save_file_dual_storage(
    file_content: bytes,
    employee_id: int,
    employee_name: str,
    file_type: str,  # "photo" | "civil_id" | "passport" | "visa"
    extension: str   # "jpg", "png", "pdf"
) -> tuple:
    """
    Save file to BOTH storage locations:
    1. Backend uploads folder (database-linked storage)
    2. Custom storage path (user-configurable manual access folder)

    Returns:
        tuple: (db_storage_path, custom_storage_path)
               custom_storage_path is None if disabled or failed
    """
    from backend.models import CompanySettings

    # Get company settings for custom storage configuration
    settings = await CompanySettings.find_one(CompanySettings.uid == 1)

    # Generate filename based on settings
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    if settings and settings.use_employee_name_in_filename:
        # Create clean employee name (only allow alphanumeric, underscores, hyphens - no path separators)
        clean_name = "".join(c for c in employee_name if c.isalnum() or c in ('_', '-'))
        # Limit length and ensure we have a safe filename component
        clean_name = clean_name[:50] or "employee"
        filename = f"{employee_id}_{clean_name}_{file_type}.{extension}"
    else:
        filename = f"emp_{employee_id}_{file_type}_{timestamp}.{extension}"

    # Ensure filename contains no path separators (defense-in-depth)
    filename = os.path.basename(filename)

    # 1. SAVE TO DATABASE STORAGE (backend/uploads)
    if file_type == "photo":
        db_dir = PHOTO_DIR
    else:
        db_dir = DOCUMENT_DIR

    db_path = os.path.join(db_dir, filename)

    # Convert to absolute path so the stored path works regardless of the
    # current working directory (avoids 404s on download when CWD differs).
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    absolute_db_path = str((project_root / db_path).resolve())

    os.makedirs(os.path.dirname(absolute_db_path), exist_ok=True)
    with open(absolute_db_path, "wb") as f:
        f.write(file_content)

    db_path = absolute_db_path
    logger.debug("File saved to absolute path for employee_id=%s type=%s path=%s", employee_id, file_type, db_path)

    # 2. SAVE TO CUSTOM LOCAL STORAGE (user-configurable folder)
    custom_path = None

    if settings and settings.enable_local_storage and settings.custom_storage_path:
        try:
            # Normalize the base path to prevent traversal via the stored setting
            base_path = os.path.normpath(settings.custom_storage_path)

            # Create organized folder structure (file_type already validated by callers)
            if file_type == "photo":
                custom_dir = os.path.join(base_path, "employees", "photos")
            elif file_type == "civil_id":
                custom_dir = os.path.join(base_path, "employees", "civil_ids")
            elif file_type == "passport":
                custom_dir = os.path.join(base_path, "employees", "passports")
            elif file_type == "visa":
                custom_dir = os.path.join(base_path, "employees", "visas")
            else:
                custom_dir = os.path.join(base_path, "employees", "documents")

            # Ensure the resolved custom_dir is still inside base_path
            custom_dir = os.path.normpath(custom_dir)
            if not (custom_dir == base_path or custom_dir.startswith(base_path + os.sep)):
                raise ValueError("Resolved custom directory is outside the configured base path")

            custom_path = os.path.join(custom_dir, filename)

            os.makedirs(custom_dir, exist_ok=True)
            with open(custom_path, "wb") as f:
                f.write(file_content)

            logger.info("File saved to custom storage for employee_id=%s type=%s", employee_id, file_type)

        except Exception as e:
            logger.warning("Failed to save to custom storage for employee_id=%s: %s", employee_id, type(e).__name__)
            # Don't fail the entire upload if custom storage fails
            custom_path = None

    return db_path, custom_path


# =============================================================================
# 1. GET EMPLOYEES (Manager-Aware Filtering)
# =============================================================================
@router.get("/", response_model=List[schemas.EmployeeFull])
async def get_all_employees(current_user: dict = Depends(get_current_active_user)):
    user_role = current_user.get("role")
    user_email = current_user.get("sub")
    
    try:
        if user_role in ["SuperAdmin", "Admin"]:
            # Admins see ALL employees (no filtering needed)
            employees = await Employee.find_all().sort(+Employee.uid).to_list()
            logger.info(f"Admin Access ({user_email}): Retrieved all {len(employees)} employees.")
        
        else:
            # Site Managers see only their assigned employees
            # Fetch manager's profile to get their UID
            me = await Admin.find_one(Admin.email == user_email)
            if not me:
                logger.error(f"Manager profile not found for email: {user_email}")
                raise HTTPException(status_code=404, detail="Manager profile not found")
            
            # Filter employees by manager_id
            employees = await Employee.find(Employee.manager_id == me.uid).sort(+Employee.uid).to_list()
            logger.info(f"Manager Access (UID: {me.uid}, Email: {user_email}): Retrieved {len(employees)} assigned employees.")

        return employees

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching employees: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")




# @router.get("/", response_model=List[schemas.EmployeeFull])
# async def get_all_employees(current_user: dict = Depends(get_current_active_user)):
#     user_role = current_user.get("role")
#     user_email = current_user.get("sub")
    
#     # Fetch current user's profile to get their UID
#     me = await Admin.find_one(Admin.email == user_email)
#     if not me:
#         raise HTTPException(status_code=404, detail="Admin profile not found")

#     try:
#         if user_role in ["SuperAdmin", "Admin"]:
#             # Owners see everyone
#             employees = await Employee.find_all().sort(+Employee.uid).to_list()
#             logger.info(f"Admin Access: Retrieved all {len(employees)} employees.")
#         else:
#             # Managers see only employees explicitly assigned to them
#             employees = await Employee.find(Employee.manager_id == me.uid).sort(+Employee.uid).to_list()
#             logger.info(f"Manager Access (ID: {me.uid}): Retrieved {len(employees)} assigned employees.")

#         return employees

#     except Exception as e:
#         logger.error(f"Error fetching employees: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")

# =============================================================================
# 2. GET SINGLE EMPLOYEE
# =============================================================================
@router.get("/{employee_id}", response_model=schemas.EmployeeFull)
async def get_employee_by_id(employee_id: int, current_user: dict = Depends(get_current_active_user)):
    emp = await Employee.find_one(Employee.uid == employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Permission Check for Managers
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if emp.manager_id != me.uid:
            raise HTTPException(status_code=403, detail="Access Denied to this employee record.")

    return emp

# =============================================================================
# 3. CREATE EMPLOYEE (Admins Only)
# =============================================================================
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.EmployeeFull)
async def create_employee(
    name: str = Form(...),
    designation: str = Form(...),
    basic_salary: float = Form(0.0),
    standard_work_days: int = Form(28),
    employee_type: str = Form("Company"),
    allowance: float = Form(0.0),
    default_hourly_rate: float = Form(0.0),
    status_field: str = Form("Active", alias="status"),
    nationality: Optional[str] = Form(None),
    permanent_address: Optional[str] = Form(None),
    phone_kuwait: Optional[str] = Form(None),
    phone_home_country: Optional[str] = Form(None),
    emergency_contact_name: Optional[str] = Form(None),
    emergency_contact_number: Optional[str] = Form(None),
    civil_id_number: Optional[str] = Form(None),
    civil_id_expiry: Optional[str] = Form(None),
    passport_number: Optional[str] = Form(None),
    passport_expiry: Optional[str] = Form(None),
    date_of_joining: Optional[str] = Form(None),
    contract_end_date: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    passport_file: Optional[UploadFile] = File(None),
    visa_file: Optional[UploadFile] = File(None),
    manager_id: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_active_user)
):
    # Only High-level admins can add new employees to the system
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create new employee records.")

    # Validate manager exists and has the correct role if provided
    if manager_id is not None:
        mgr = await Admin.find_one(Admin.uid == manager_id)
        if not mgr or mgr.role != "Site Manager":
            raise HTTPException(status_code=400, detail="Invalid manager ID: must be an active Site Manager.")

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        passport_path = None
        visa_path = None

        if passport_file and passport_file.filename:
            passport_path = os.path.join(UPLOAD_DIRECTORY, "passports", f"pp_{timestamp}_{passport_file.filename}")
            save_upload_file(passport_file, passport_path)

        if visa_file and visa_file.filename:
            visa_path = os.path.join(UPLOAD_DIRECTORY, "visas", f"visa_{timestamp}_{visa_file.filename}")
            save_upload_file(visa_file, visa_path)

        # Parse date fields (return datetime for BSON/MongoDB compatibility)
        def parse_date(val):
            if not val:
                return None
            try:
                from datetime import date as date_type, datetime as datetime_type
                d = date_type.fromisoformat(val)
                return datetime_type(d.year, d.month, d.day)
            except (ValueError, TypeError):
                return None

        new_uid = await get_next_uid("employees")
        new_employee = Employee(
            uid=new_uid,
            name=name,
            designation=designation,
            basic_salary=basic_salary,
            standard_work_days=standard_work_days,
            employee_type=employee_type,
            allowance=allowance,
            default_hourly_rate=default_hourly_rate,
            status=status_field,
            nationality=nationality,
            permanent_address=permanent_address,
            phone_kuwait=phone_kuwait,
            phone_home_country=phone_home_country,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_number=emergency_contact_number,
            civil_id_number=civil_id_number,
            civil_id_expiry=parse_date(civil_id_expiry),
            passport_number=passport_number,
            passport_expiry=parse_date(passport_expiry),
            date_of_joining=parse_date(date_of_joining),
            contract_end_date=parse_date(contract_end_date),
            date_of_birth=parse_date(date_of_birth),
            passport_path=passport_path,
            visa_path=visa_path,
            manager_id=manager_id
        )
        
        await new_employee.insert()
        
        # Broadcast via WebSocket - use schema to convert uid → id correctly
        emp_dict = schemas.EmployeeFull.model_validate(new_employee).model_dump(mode='json')
        await manager.broadcast(json.dumps({"type": "employee_update", "data": emp_dict}))
        
        return new_employee

    except Exception as e:
        logger.error(f"Creation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create employee")

# =============================================================================
# 4. UPDATE EMPLOYEE (Admins Only - Managers have view-only access)
# =============================================================================
@router.put("/{employee_id}", response_model=schemas.EmployeeFull)
async def update_employee(
    employee_id: int, 
    employee_update: schemas.EmployeeUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    # Only SuperAdmin and Admin can edit employee details (including salary/allowance)
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admins can edit employee details. Site Managers have view-only access."
        )

    emp = await Employee.find_one(Employee.uid == employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Apply updates
    data = employee_update.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(emp, key, value)
    
    await emp.save()
    
    # WebSocket Broadcast - use schema to convert uid → id correctly
    emp_dict = schemas.EmployeeFull.model_validate(emp).model_dump(mode='json')
    await manager.broadcast(json.dumps({"type": "employee_update", "data": emp_dict}))
    
    return emp

# =============================================================================
# 5. DELETE EMPLOYEE (Admins Only)
# =============================================================================
@router.delete("/{employee_id}", status_code=204)
async def delete_employee(employee_id: int, current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can delete employees from the system.")

    emp = await Employee.find_one(Employee.uid == employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await emp.delete()
    
    # WebSocket Broadcast delete event
    await manager.broadcast(json.dumps({"type": "employee_delete", "id": employee_id}))
    
    return None


# =============================================================================
# 6. UPLOAD EMPLOYEE PHOTO
# =============================================================================

# Map content-type → safe file extension (avoids using user-provided filename)
_CONTENT_TYPE_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

@router.post("/{employee_id}/upload-photo")
async def upload_employee_photo(
    employee_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Upload employee photo with dual storage (database + custom folder)"""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can upload employee photos.")

    # Read file content FIRST (before any content_type check)
    content = await file.read()

    # Validate file size (max 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")

    # Validate file signature (magic bytes) - PRIMARY validation
    is_jpeg = len(content) >= 3 and content[:3] == b"\xff\xd8\xff"
    is_png = len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n"
    is_gif = len(content) >= 6 and content[:6] in (b"GIF87a", b"GIF89a")
    is_webp = len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_gif or is_webp):
        raise HTTPException(
            status_code=400,
            detail="File content does not match an allowed image format (JPEG, PNG, GIF, WebP)"
        )

    # Log warning if content_type header is missing/invalid (but don't fail)
    if not file.content_type or not file.content_type.startswith("image/"):
        logger.warning(
            "Photo upload for employee %s has missing/invalid content_type header (got: %s), but file content is valid",
            employee_id,
            file.content_type or "None"
        )

    emp = await Employee.find_one(Employee.uid == employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Delete old files if they exist
    if emp.photo_path and os.path.exists(emp.photo_path):
        try:
            os.remove(emp.photo_path)
        except OSError:
            pass

    if emp.custom_photo_path and os.path.exists(emp.custom_photo_path):
        try:
            os.remove(emp.custom_photo_path)
        except OSError:
            pass

    # Derive extension from content-type if available, otherwise from magic bytes
    if file.content_type and file.content_type.lower() in _CONTENT_TYPE_EXT:
        ext = _CONTENT_TYPE_EXT[file.content_type.lower()]
    elif is_jpeg:
        ext = "jpg"
    elif is_png:
        ext = "png"
    elif is_gif:
        ext = "gif"
    else:
        ext = "webp"

    # Save to BOTH storage locations
    db_path, custom_path = await save_file_dual_storage(
        content,
        employee_id,
        emp.name,
        "photo",
        ext
    )

    # Update employee record with both paths
    emp.photo_path = db_path
    emp.custom_photo_path = custom_path
    emp.updated_at = datetime.datetime.now()
    await emp.save()

    logger.info("Photo uploaded for employee_id=%s ext=%s dual_storage=%s", employee_id, ext, custom_path is not None)
    return {
        "message": "Photo uploaded successfully",
        "db_path": db_path,
        "custom_path": custom_path,
        "dual_storage_enabled": custom_path is not None
    }


# =============================================================================
# 7. UPLOAD EMPLOYEE DOCUMENT
# =============================================================================
_VALID_DOCUMENT_TYPES = frozenset(["civil_id", "passport", "visa"])

@router.post("/{employee_id}/upload-document")
async def upload_employee_document(
    employee_id: int,
    document_type: str = Query(..., description="'civil_id' | 'passport' | 'visa'"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Upload employee documents with dual storage (database + custom folder)"""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can upload employee documents.")

    if document_type not in _VALID_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid document type. Must be 'civil_id', 'passport', or 'visa'.")

    # Read file content FIRST (before any content_type check)
    content = await file.read()

    # Validate file size (max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")

    # Validate PDF magic bytes - PRIMARY validation
    if not (len(content) >= 4 and content[:4] == b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="File content is not a valid PDF document"
        )

    # Log warning if content_type header is missing/invalid (but don't fail)
    if file.content_type != "application/pdf":
        logger.warning(
            "Document upload for employee %s has missing/invalid content_type header (got: %s), but file content is valid PDF",
            employee_id,
            file.content_type or "None"
        )

    emp = await Employee.find_one(Employee.uid == employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Save to BOTH storage locations
    db_path, custom_path = await save_file_dual_storage(
        content,
        employee_id,
        emp.name,
        document_type,
        "pdf"
    )

    # Determine old paths and update employee record fields
    old_db_path = None
    old_custom_path = None

    if document_type == "civil_id":
        old_db_path = emp.civil_id_document_path
        old_custom_path = emp.custom_civil_id_path
        emp.civil_id_document_path = db_path
        emp.custom_civil_id_path = custom_path
    elif document_type == "passport":
        old_db_path = emp.passport_document_path
        old_custom_path = emp.custom_passport_path
        emp.passport_document_path = db_path
        emp.custom_passport_path = custom_path
    elif document_type == "visa":
        old_db_path = emp.visa_document_path
        old_custom_path = emp.custom_visa_path
        emp.visa_document_path = db_path
        emp.custom_visa_path = custom_path

    # Remove old files
    for old_path in [old_db_path, old_custom_path]:
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    emp.updated_at = datetime.datetime.now()
    await emp.save()

    logger.info("Document uploaded for employee_id=%s type=%s dual_storage=%s", employee_id, document_type, custom_path is not None)
    return {
        "message": f"{document_type} document uploaded successfully",
        "db_path": db_path,
        "custom_path": custom_path,
        "dual_storage_enabled": custom_path is not None
    }


# =============================================================================
# 8. DOWNLOAD EMPLOYEE DOCUMENT / PHOTO
# =============================================================================
@download_router.get("/{employee_id}/download/{document_type}")
async def download_employee_document(
    request: Request,
    employee_id: int,
    document_type: str,
    token: Optional[str] = Query(None),
):
    """
    Download employee document or photo.
    Accepts authentication token as query parameter for use in <img> tags,
    or via the standard Authorization: Bearer <token> header.
    """
    from jose import jwt, JWTError
    from backend.security import SECRET_KEY, ALGORITHM

    # Determine the raw JWT string - prefer query param, then Authorization header
    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[len("Bearer "):]

    if not raw_token:
        raise HTTPException(status_code=401, detail="Authentication token required")

    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await Admin.find_one(Admin.email == email)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid or inactive user")
        current_user = payload
    except JWTError:
        logger.warning("Invalid or expired token used for document download (employee_id=%s)", employee_id)
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

    emp = await Employee.find_one(Employee.uid == employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Permission check for managers
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or emp.manager_id != me.uid:
            raise HTTPException(status_code=403, detail="Access denied.")

    file_path = None
    if document_type == "photo":
        file_path = emp.photo_path
    elif document_type == "civil_id":
        file_path = emp.civil_id_document_path
    elif document_type == "passport":
        file_path = emp.passport_document_path or emp.passport_path
    elif document_type == "visa":
        file_path = emp.visa_document_path or emp.visa_path
    else:
        raise HTTPException(status_code=400, detail="Invalid document type.")

    # If the stored path is relative, resolve it against the project root so that
    # os.path.exists() works regardless of the current working directory.
    if file_path and not os.path.isabs(file_path):
        project_root = pathlib.Path(__file__).resolve().parent.parent.parent
        file_path = str((project_root / file_path).resolve())

    file_exists = os.path.exists(file_path) if file_path else False
    logger.debug(
        "Serving document for employee_id=%s type=%s exists=%s",
        employee_id, document_type, file_exists
    )

    if not file_path or not file_exists:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = os.path.basename(file_path)
    if document_type == "photo":
        return FileResponse(file_path, filename=filename)
    # Use inline disposition so PDFs render in-browser (preview).
    # Strip control characters (including CR/LF) and escape double-quotes to
    # prevent HTTP header injection.
    safe_filename = filename.replace("\r", "").replace("\n", "").replace('"', '\\"')
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )





























# router = APIRouter(
#     prefix="/employees",
#     tags=["Employees"],
#     dependencies=[Depends(get_current_active_user)]
# )

# UPLOAD_DIRECTORY = os.path.join("backend", "uploads")

# def save_upload_file(upload_file: UploadFile, destination: str) -> str:
#     try:
#         os.makedirs(os.path.dirname(destination), exist_ok=True)
#         with open(destination, "wb") as buffer:
#             shutil.copyfileobj(upload_file.file, buffer)
#     finally:
#         upload_file.file.close()
#     return destination

# @router.get("/", response_model=List[schemas.EmployeeFull])
# async def get_all_employees(current_user: dict = Depends(get_current_active_user)):
#     user_role = current_user.get("role")
    
#     if user_role in ["SuperAdmin", "Admin"]:
#         return await Employee.find_all().sort(+Employee.id).to_list()

#     elif user_role == "Site Manager":
#         # Logic: Filter employees who have been scheduled at the manager's sites
#         # This is a bit complex in NoSQL without joins.
#         # For now, we return all employees to ensure the frontend loads.
#         # You can refine this permission logic later.
#         return await Employee.find_all().to_list()
    
#     raise HTTPException(status_code=403, detail="Access Denied")

# @router.get("/{employee_id}", response_model=schemas.EmployeeFull)
# async def get_employee_by_id(employee_id: int):
#     emp = await Employee.find_one(Employee.uid == employee_id)
#     if not emp:
#         raise HTTPException(status_code=404, detail="Employee not found")
#     return emp

# @router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.EmployeeFull)
# async def create_employee(
#     name: str = Form(...),
#     designation: str = Form(...),
#     basic_salary: float = Form(...),
#     standard_work_days: int = Form(...),
#     passport_file: UploadFile = File(...),
#     visa_file: UploadFile = File(...)
# ):
#     # 1. Handle Files
#     timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#     passport_path = os.path.join(UPLOAD_DIRECTORY, "passports", f"pp_{timestamp}_{passport_file.filename}")
#     visa_path = os.path.join(UPLOAD_DIRECTORY, "visas", f"visa_{timestamp}_{visa_file.filename}")
    
#     save_upload_file(passport_file, passport_path)
#     save_upload_file(visa_file, visa_path)

#     # 2. Create in Mongo
#     new_uid = await get_next_uid("employees")
    
#     new_employee = Employee(
#         uid=new_uid,
#         name=name,
#         designation=designation,
#         basic_salary=basic_salary,
#         standard_work_days=standard_work_days,
#         passport_path=passport_path,
#         visa_path=visa_path,
#         status="Active",
#         allowance=0.0,
#         default_hourly_rate=0.0
#     )
    
#     await new_employee.insert()
    
#     # 3. Broadcast
#     # We convert to dict and manually set 'id' to 'uid' for the frontend socket
#     emp_dict = new_employee.model_dump()
#     emp_dict['id'] = new_employee.uid
#     await manager.broadcast(json.dumps({"type": "employee_update", "data": emp_dict}))
    
#     return new_employee

# @router.delete("/{employee_id}", status_code=204)
# async def delete_employee(employee_id: int):
#     emp = await Employee.find_one(Employee.uid == employee_id)
#     if not emp:
#         raise HTTPException(status_code=404, detail="Employee not found")
    
#     await emp.delete()
#     return None