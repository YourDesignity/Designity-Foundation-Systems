import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Query, Request
from fastapi.responses import FileResponse

from backend import schemas
from backend.security import get_current_active_user
from backend.services.hr.employee_service import EmployeeService
from backend.utils.logger import setup_logger

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

_service = EmployeeService()


# =============================================================================
# 1. GET EMPLOYEES (Manager-Aware Filtering)
# =============================================================================
@router.get("/", response_model=List[schemas.EmployeeFull])
async def get_all_employees(current_user: dict = Depends(get_current_active_user)):
    try:
        return await _service.get_employees_for_user(
            current_user.get("role"), current_user.get("sub")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching employees: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# =============================================================================
# 2. GET SINGLE EMPLOYEE
# =============================================================================
@router.get("/{employee_id}", response_model=schemas.EmployeeFull)
async def get_employee_by_id(employee_id: int, current_user: dict = Depends(get_current_active_user)):
    return await _service.get_employee_with_access_check(
        employee_id, current_user.get("role"), current_user.get("sub")
    )

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
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create new employee records.")

    try:
        data = {
            "name": name, "designation": designation, "basic_salary": basic_salary,
            "standard_work_days": standard_work_days, "employee_type": employee_type,
            "allowance": allowance, "default_hourly_rate": default_hourly_rate,
            "status_field": status_field, "nationality": nationality,
            "permanent_address": permanent_address, "phone_kuwait": phone_kuwait,
            "phone_home_country": phone_home_country,
            "emergency_contact_name": emergency_contact_name,
            "emergency_contact_number": emergency_contact_number,
            "civil_id_number": civil_id_number, "civil_id_expiry": civil_id_expiry,
            "passport_number": passport_number, "passport_expiry": passport_expiry,
            "date_of_joining": date_of_joining, "contract_end_date": contract_end_date,
            "date_of_birth": date_of_birth, "manager_id": manager_id,
        }
        new_employee = await _service.create_employee_with_files(data, passport_file, visa_file)

        emp_dict = schemas.EmployeeFull.model_validate(new_employee).model_dump(mode='json')
        await manager.broadcast(json.dumps({"type": "employee_update", "data": emp_dict}))

        return new_employee

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Creation Error: %s", e)
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
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admins can edit employee details. Site Managers have view-only access."
        )

    data = employee_update.model_dump(exclude_unset=True)
    emp = await _service.update_employee_fields(employee_id, data)

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

    await _service.delete_employee(employee_id)

    await manager.broadcast(json.dumps({"type": "employee_delete", "id": employee_id}))

    return None


# =============================================================================
# 6. UPLOAD EMPLOYEE PHOTO
# =============================================================================

@router.post("/{employee_id}/upload-photo")
async def upload_employee_photo(
    employee_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Upload employee photo with dual storage (database + custom folder)"""
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can upload employee photos.")

    content = await file.read()
    return await _service.upload_photo(employee_id, content, file.content_type)


# =============================================================================
# 7. UPLOAD EMPLOYEE DOCUMENT
# =============================================================================

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

    content = await file.read()
    return await _service.upload_document(employee_id, document_type, content, file.content_type)


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
    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[len("Bearer "):]

    result = await _service.download_document(employee_id, document_type, raw_token)

    if result["is_photo"]:
        return FileResponse(result["file_path"], filename=result["filename"])

    safe_filename = result["filename"].replace("\r", "").replace("\n", "").replace('"', '\\"')
    return FileResponse(
        result["file_path"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )

