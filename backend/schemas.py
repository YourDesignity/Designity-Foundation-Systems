from typing import List, Optional
from datetime import date
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# =============================================================================
# 1. DESIGNATION SCHEMAS
# =============================================================================
class DesignationBase(BaseModel):
    title: str

class DesignationCreate(DesignationBase):
    pass

class DesignationResponse(DesignationBase):
    """
    Designation response schema.
    Field Mapping: Database ``uid`` → API ``id`` (via validation_alias).
    """
    id: int = Field(..., validation_alias="uid")
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 2. EMPLOYEE SCHEMAS
# =============================================================================
class EmployeeBase(BaseModel):
    id: int = Field(..., validation_alias="uid")
    name: str
    designation: str
    status: str

class EmployeePublic(EmployeeBase):
    """
    Employee public schema for API responses.
    Field Mapping: Database ``uid`` → API ``id`` (via validation_alias).
    Return the model directly or use ``schemas.EmployeePublic.model_validate(obj).model_dump(mode='json')``
    for manual serialization; do NOT manually build dicts with ``"id": obj.uid``
    as that bypasses Pydantic and breaks schema validation.
    """
    model_config = ConfigDict(from_attributes=True)

class EmployeeFull(EmployeeBase):
    """
    Full employee schema including financial and document fields.
    Field Mapping: Database ``uid`` → API ``id`` (via validation_alias).
    Return the model directly or use ``schemas.EmployeeFull.model_validate(obj).model_dump(mode='json')``
    for manual serialization; do NOT manually build dicts with ``"id": obj.uid``
    as that bypasses Pydantic and breaks schema validation.
    """
    # Financial
    basic_salary: float
    allowance: float
    standard_work_days: int
    default_hourly_rate: float

    # Employee type
    employee_type: str = "Company"

    # Personal details
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    permanent_address: Optional[str] = None

    # Contact information
    phone_kuwait: Optional[str] = None
    phone_home_country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None

    # Identity documents
    civil_id_number: Optional[str] = None
    civil_id_expiry: Optional[date] = None
    civil_id_document_path: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    passport_document_path: Optional[str] = None
    visa_document_path: Optional[str] = None

    # Photo
    photo_path: Optional[str] = None

    # Employment details
    date_of_joining: Optional[date] = None
    contract_end_date: Optional[date] = None

    # Deprecated document paths (kept for backward compatibility)
    passport_path: Optional[str] = None
    visa_path: Optional[str] = None

    manager_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class EmployeeCreate(BaseModel):
    name: str
    designation: str
    basic_salary: float = 0.0
    allowance: float = 0.0
    standard_work_days: int = 28
    status: str = "Active"
    employee_type: str = "Company"
    default_hourly_rate: float = 0.0
    nationality: Optional[str] = None
    permanent_address: Optional[str] = None
    phone_kuwait: Optional[str] = None
    phone_home_country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    civil_id_number: Optional[str] = None
    civil_id_expiry: Optional[date] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    date_of_joining: Optional[date] = None
    contract_end_date: Optional[date] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    designation: Optional[str] = None
    basic_salary: Optional[float] = None
    allowance: Optional[float] = None
    standard_work_days: Optional[int] = None
    status: Optional[str] = None
    manager_id: Optional[int] = None
    employee_type: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    permanent_address: Optional[str] = None
    phone_kuwait: Optional[str] = None
    phone_home_country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    civil_id_number: Optional[str] = None
    civil_id_expiry: Optional[date] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    default_hourly_rate: Optional[float] = None
    date_of_joining: Optional[date] = None
    contract_end_date: Optional[date] = None

# =============================================================================
# 3. ADMIN SCHEMAS
# =============================================================================
class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    designation: str
    role: str 

class AdminUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    phone: Optional[str] = None

class AdminPasswordUpdate(BaseModel):
    new_password: str

class AdminPublic(BaseModel):
    """
    Admin public schema for API responses.
    Field Mapping: Database ``uid`` → API ``id`` (via validation_alias).

    Usage::

        # ✅ CORRECT – return model directly; FastAPI/Pydantic converts uid → id
        return admin

        # ✅ CORRECT – explicit conversion
        return admin.model_dump(by_alias=True)

        # ❌ WRONG – manual dict breaks validation (schema expects 'uid' as input)
        return {"id": admin.uid, "email": admin.email}
    """
    id: int = Field(..., validation_alias="uid")
    email: EmailStr
    full_name: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AdminSelfUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# =============================================================================
# 4. SITE SCHEMAS
# =============================================================================
class SiteBase(BaseModel):
    name: str
    location: str
    site_manager: Optional[str] = None 
    description: Optional[str] = None 
    phone: Optional[str] = None

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    site_manager: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class SiteResponse(SiteBase):
    """
    Site response schema.
    Field Mapping: Database ``uid`` → API ``id`` (via validation_alias).
    """
    id: int = Field(..., validation_alias="uid")
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 5. SCHEDULE SCHEMAS
# =============================================================================
class ScheduleCreate(BaseModel):
    site_id: int
    employee_ids: List[int]
    start_date: str 
    end_date: str   
    task: str
    shift_type: Optional[str] = None

class ScheduleResponse(BaseModel):
    """
    Schedule response schema.
    Field Mapping: Database ``uid`` → API ``id``, ``employee_uid`` → ``employee_id``,
    ``site_uid`` → ``site_id`` (all via validation_alias).
    """
    id: int = Field(..., validation_alias="uid")
    employee_id: int = Field(..., validation_alias="employee_uid")
    site_id: int = Field(..., validation_alias="site_uid")
    work_date: str
    task: str
    shift_type: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# 6. ATTENDANCE SCHEMAS
# =============================================================================
class AttendanceRecord(BaseModel):
    employee_id: int
    date: str
    status: str
    shift: Optional[str] = "Morning"
    overtime_hours: Optional[int] = 0 

class AttendanceUpdateBatch(BaseModel):
    records: List[AttendanceRecord]

# =============================================================================
# 7. DUTY LIST SCHEMAS
# =============================================================================
class DutyAssignmentCreate(BaseModel):
    employee_id: int
    site_id: int
    manager_id: int
    start_date: str
    end_date: str

# =============================================================================
# 8. PAYSLIP / FINANCIAL SCHEMAS
# =============================================================================
class PayslipRequest(BaseModel):
    employee_ids: List[int]
    pay_period: str 

class DeductionCreate(BaseModel):
    employee_id: int
    pay_period: str 
    amount: float
    reason: str

class OvertimeCreate(BaseModel):
    employee_id: int
    date: str
    hours: float
    type: str = "Normal"