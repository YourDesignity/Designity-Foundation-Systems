"""Service layer for employee business operations."""

import logging
import os
import pathlib
import shutil
from datetime import date, datetime, timedelta
from typing import Any, List, Optional, Tuple

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")

UPLOAD_DIRECTORY = os.path.join("backend", "uploads")
PHOTO_DIR = os.path.join(UPLOAD_DIRECTORY, "photos")
DOCUMENT_DIR = os.path.join(UPLOAD_DIRECTORY, "documents")

os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(DOCUMENT_DIR, exist_ok=True)

_CONTENT_TYPE_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

_VALID_DOCUMENT_TYPES = frozenset(["civil_id", "passport", "visa"])


class EmployeeService(BaseService):
    """Employee lifecycle, search, and compliance operations."""

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    @staticmethod
    def _parse_date(value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        if isinstance(value, str):
            try:
                d = date.fromisoformat(value)
                return datetime(d.year, d.month, d.day)
            except ValueError:
                return None
        return None

    async def create_employee(self, payload: Any):
        """
        Create a new employee record.

        Validations:
        - Optional manager_id must reference a Site Manager
        - Date fields are normalized for BSON compatibility

        Args:
            payload: Employee create payload (dict or schema/model)

        Returns:
            Created Employee document

        Raises:
            HTTPException 400: Invalid manager reference
        """
        from backend.models import Admin, Employee

        data = self._to_dict(payload)
        manager_id = data.get("manager_id")
        if manager_id is not None:
            mgr = await Admin.find_one(Admin.uid == manager_id)
            if not mgr or mgr.role != "Site Manager":
                self.raise_bad_request("Invalid manager ID: must be an active Site Manager")

        new_uid = await self.get_next_uid("employees")
        employee = Employee(
            uid=new_uid,
            name=data.get("name", ""),
            designation=data.get("designation", ""),
            basic_salary=float(data.get("basic_salary", 0.0)),
            standard_work_days=int(data.get("standard_work_days", 28)),
            employee_type=data.get("employee_type", "Company"),
            allowance=float(data.get("allowance", 0.0)),
            default_hourly_rate=float(data.get("default_hourly_rate", 0.0)),
            status=data.get("status") or data.get("status_field", "Active"),
            nationality=data.get("nationality"),
            permanent_address=data.get("permanent_address"),
            phone_kuwait=data.get("phone_kuwait"),
            phone_home_country=data.get("phone_home_country"),
            emergency_contact_name=data.get("emergency_contact_name"),
            emergency_contact_number=data.get("emergency_contact_number"),
            civil_id_number=data.get("civil_id_number"),
            civil_id_expiry=self._parse_date(data.get("civil_id_expiry")),
            passport_number=data.get("passport_number"),
            passport_expiry=self._parse_date(data.get("passport_expiry")),
            date_of_joining=self._parse_date(data.get("date_of_joining")),
            contract_end_date=self._parse_date(data.get("contract_end_date")),
            date_of_birth=self._parse_date(data.get("date_of_birth")),
            passport_path=data.get("passport_path"),
            visa_path=data.get("visa_path"),
            manager_id=manager_id,
        )
        await employee.insert()
        logger.info("Employee created: %s (ID: %s)", employee.name, employee.uid)
        return employee

    async def update_employee(self, employee_id: int, payload: Any):
        """
        Update employee details.

        Validations:
        - Employee must exist
        - Optional manager_id must reference Site Manager

        Args:
            employee_id: Employee UID
            payload: Employee update payload

        Returns:
            Updated Employee document

        Raises:
            HTTPException 404: Employee not found
            HTTPException 400: Invalid manager reference
        """
        from backend.models import Admin, Employee

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found("Employee not found")

        update_data = self._to_dict(payload)
        manager_id = update_data.get("manager_id")
        if manager_id is not None:
            mgr = await Admin.find_one(Admin.uid == manager_id)
            if not mgr or mgr.role != "Site Manager":
                self.raise_bad_request("Invalid manager ID: must be an active Site Manager")

        for key, value in update_data.items():
            if key in {
                "date_of_birth",
                "civil_id_expiry",
                "passport_expiry",
                "date_of_joining",
                "contract_end_date",
            }:
                setattr(employee, key, self._parse_date(value))
            else:
                setattr(employee, key, value)

        await employee.save()
        logger.info("Employee updated")
        return employee

    async def search_employees(
        self,
        query: Optional[str] = None,
        designation: Optional[str] = None,
        status: Optional[str] = None,
        manager_id: Optional[int] = None,
        employee_type: Optional[str] = None,
    ) -> List[Any]:
        """
        Search employees with optional filters.

        Validations:
        - All filters are optional and combined using AND semantics

        Args:
            query: Text query for name/civil_id/passport
            designation: Designation filter
            status: Employee status filter
            manager_id: Manager UID filter
            employee_type: Company/Outsourced filter

        Returns:
            Employee list sorted by UID
        """
        from backend.models import Employee

        filters = []
        if designation:
            filters.append(Employee.designation == designation)
        if status:
            filters.append(Employee.status == status)
        if manager_id is not None:
            filters.append(Employee.manager_id == manager_id)
        if employee_type:
            filters.append(Employee.employee_type == employee_type)

        if query:
            needle = query.strip().lower()
            candidates = await (Employee.find(*filters).sort("+uid").to_list() if filters else Employee.find_all().sort("+uid").to_list())
            return [
                emp
                for emp in candidates
                if needle in (emp.name or "").lower()
                or needle in (emp.designation or "").lower()
                or needle in (emp.civil_id_number or "").lower()
                or needle in (emp.passport_number or "").lower()
            ]

        return await (Employee.find(*filters).sort("+uid").to_list() if filters else Employee.find_all().sort("+uid").to_list())

    async def get_expiring_documents(self, within_days: int = 30) -> list[dict]:
        """
        Get employees whose Civil ID or Passport expires soon.

        Validations:
        - within_days must be non-negative

        Args:
            within_days: Non-negative days-ahead window
                        (0 returns documents expiring today)

        Returns:
            List of expiring document summary rows
        """
        from backend.models import Employee

        if within_days < 0:
            self.raise_bad_request("within_days must be non-negative")

        now = datetime.combine(date.today(), datetime.min.time())
        window_end = now + timedelta(days=within_days)
        employees = await Employee.find_all().to_list()

        rows: list[dict] = []
        for emp in employees:
            if emp.civil_id_expiry and now <= emp.civil_id_expiry <= window_end:
                rows.append(
                    {
                        "employee_id": emp.uid,
                        "employee_name": emp.name,
                        "document_type": "civil_id",
                        "expiry_date": emp.civil_id_expiry.date().isoformat(),
                        "days_remaining": (emp.civil_id_expiry - now).days,
                    }
                )
            if emp.passport_expiry and now <= emp.passport_expiry <= window_end:
                rows.append(
                    {
                        "employee_id": emp.uid,
                        "employee_name": emp.name,
                        "document_type": "passport",
                        "expiry_date": emp.passport_expiry.date().isoformat(),
                        "days_remaining": (emp.passport_expiry - now).days,
                    }
                )
        return sorted(rows, key=lambda item: item["days_remaining"])

    async def get_employee_by_id(self, employee_id: int):
        from backend.models import Employee

        employee = await Employee.find_one(Employee.uid == employee_id)
        if not employee:
            self.raise_not_found(f"Employee {employee_id} not found")
        return employee

    async def get_employee_if_exists(self, employee_id: int):
        from backend.models import Employee

        return await Employee.find_one(Employee.uid == employee_id)

    async def get_employees(self):
        from backend.models import Employee

        return await Employee.find_all().sort("+uid").to_list()

    async def delete_employee(self, employee_id: int) -> bool:
        employee = await self.get_employee_by_id(employee_id)
        await employee.delete()
        logger.info("Employee deleted")
        return True

    async def validate_designation(self, employee_id: int, expected_designation: str, detail_prefix: str):
        employee = await self.get_employee_if_exists(employee_id)
        if employee and employee.designation != expected_designation:
            self.raise_bad_request(
                f"{detail_prefix} designation '{employee.designation}' does not match slot designation '{expected_designation}'"
            )
        return employee

    async def get_available_employees_by_designation(self, designation: str) -> List[Any]:
        from backend.models import Employee

        return await Employee.find(
            Employee.designation == designation,
            Employee.status == "Active",
            Employee.availability_status == "Available",
        ).to_list()

    # ====================================================================
    # FILE HELPERS
    # ====================================================================

    @staticmethod
    def save_upload_file(upload_file: Any, destination: str) -> str:
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            logger.debug("File Saved: %s", destination)
        except Exception as e:
            logger.error("File Save Error: %s", e)
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Could not save file.")
        finally:
            upload_file.file.close()
        return destination

    @staticmethod
    async def save_file_dual_storage(
        file_content: bytes,
        employee_id: int,
        employee_name: str,
        file_type: str,
        extension: str,
    ) -> Tuple[str, Optional[str]]:
        """Save file to both database storage and optional custom storage."""
        from backend.models import CompanySettings

        settings = await CompanySettings.find_one(CompanySettings.uid == 1)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        if settings and settings.use_employee_name_in_filename:
            clean_name = "".join(
                c for c in employee_name if c.isalnum() or c in ("_", "-")
            )
            clean_name = clean_name[:50] or "employee"
            filename = f"{employee_id}_{clean_name}_{file_type}.{extension}"
        else:
            filename = f"emp_{employee_id}_{file_type}_{timestamp}.{extension}"

        filename = os.path.basename(filename)

        # 1. Database storage
        db_dir = PHOTO_DIR if file_type == "photo" else DOCUMENT_DIR
        db_path = os.path.join(db_dir, filename)

        project_root = pathlib.Path(__file__).resolve().parent.parent.parent
        absolute_db_path = str((project_root / db_path).resolve())

        os.makedirs(os.path.dirname(absolute_db_path), exist_ok=True)
        with open(absolute_db_path, "wb") as f:
            f.write(file_content)

        db_path = absolute_db_path
        logger.debug(
            "File saved to absolute path for employee_id=%s type=%s path=%s",
            employee_id, file_type, db_path,
        )

        # 2. Custom local storage
        custom_path = None
        if settings and settings.enable_local_storage and settings.custom_storage_path:
            try:
                base_path = os.path.normpath(settings.custom_storage_path)

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

                custom_dir = os.path.normpath(custom_dir)
                if not (
                    custom_dir == base_path
                    or custom_dir.startswith(base_path + os.sep)
                ):
                    raise ValueError(
                        "Resolved custom directory is outside the configured base path"
                    )

                custom_path = os.path.join(custom_dir, filename)
                os.makedirs(custom_dir, exist_ok=True)
                with open(custom_path, "wb") as f:
                    f.write(file_content)

                logger.info(
                    "File saved to custom storage for employee_id=%s type=%s",
                    employee_id, file_type,
                )
            except Exception:
                logger.warning(
                    "Failed to save to custom storage for employee_id=%s",
                    employee_id,
                )
                custom_path = None

        return db_path, custom_path

    # ====================================================================
    # ROLE-AWARE QUERIES
    # ====================================================================

    async def get_employees_for_user(self, user_role: str, user_email: str) -> List[Any]:
        """Get employees filtered by user role: admins see all, managers see their own."""
        from backend.models import Admin, Employee

        if user_role in ["SuperAdmin", "Admin"]:
            employees = await Employee.find_all().sort("+uid").to_list()
            logger.info("Admin Access (%s): Retrieved all %d employees.", user_email, len(employees))
            return employees

        me = await Admin.find_one(Admin.email == user_email)
        if not me:
            logger.error("Manager profile not found for email: %s", user_email)
            self.raise_not_found("Manager profile not found")

        employees = await Employee.find(Employee.manager_id == me.uid).sort("+uid").to_list()
        logger.info(
            "Manager Access (UID: %s, Email: %s): Retrieved %d assigned employees.",
            me.uid, user_email, len(employees),
        )
        return employees

    async def get_employee_with_access_check(
        self, employee_id: int, user_role: str, user_email: str
    ) -> Any:
        """Get single employee with permission check for managers."""
        from backend.models import Admin, Employee

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            self.raise_not_found("Employee not found")

        if user_role not in ["SuperAdmin", "Admin"]:
            me = await Admin.find_one(Admin.email == user_email)
            if emp.manager_id != me.uid:
                self.raise_forbidden("Access Denied to this employee record.")

        return emp

    # ====================================================================
    # CREATE EMPLOYEE WITH FILES
    # ====================================================================

    async def create_employee_with_files(
        self, data: dict, passport_file: Any = None, visa_file: Any = None
    ) -> Any:
        """Create employee, optionally saving passport/visa files."""
        from backend.models import Admin, Employee

        manager_id = data.get("manager_id")
        if manager_id is not None:
            mgr = await Admin.find_one(Admin.uid == manager_id)
            if not mgr or mgr.role != "Site Manager":
                self.raise_bad_request("Invalid manager ID: must be an active Site Manager.")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        passport_path = None
        visa_path = None

        if passport_file and passport_file.filename:
            passport_path = os.path.join(
                UPLOAD_DIRECTORY, "passports", f"pp_{timestamp}_{passport_file.filename}"
            )
            self.save_upload_file(passport_file, passport_path)

        if visa_file and visa_file.filename:
            visa_path = os.path.join(
                UPLOAD_DIRECTORY, "visas", f"visa_{timestamp}_{visa_file.filename}"
            )
            self.save_upload_file(visa_file, visa_path)

        new_uid = await self.get_next_uid("employees")
        new_employee = Employee(
            uid=new_uid,
            name=data.get("name", ""),
            designation=data.get("designation", ""),
            basic_salary=float(data.get("basic_salary", 0.0)),
            standard_work_days=int(data.get("standard_work_days", 28)),
            employee_type=data.get("employee_type", "Company"),
            allowance=float(data.get("allowance", 0.0)),
            default_hourly_rate=float(data.get("default_hourly_rate", 0.0)),
            status=data.get("status_field", "Active"),
            nationality=data.get("nationality"),
            permanent_address=data.get("permanent_address"),
            phone_kuwait=data.get("phone_kuwait"),
            phone_home_country=data.get("phone_home_country"),
            emergency_contact_name=data.get("emergency_contact_name"),
            emergency_contact_number=data.get("emergency_contact_number"),
            civil_id_number=data.get("civil_id_number"),
            civil_id_expiry=self._parse_date(data.get("civil_id_expiry")),
            passport_number=data.get("passport_number"),
            passport_expiry=self._parse_date(data.get("passport_expiry")),
            date_of_joining=self._parse_date(data.get("date_of_joining")),
            contract_end_date=self._parse_date(data.get("contract_end_date")),
            date_of_birth=self._parse_date(data.get("date_of_birth")),
            passport_path=passport_path,
            visa_path=visa_path,
            manager_id=manager_id,
        )
        await new_employee.insert()
        logger.info("Employee created: %s (ID: %s)", new_employee.name, new_employee.uid)
        return new_employee

    # ====================================================================
    # UPDATE WITH BROADCAST
    # ====================================================================

    async def update_employee_fields(self, employee_id: int, update_data: dict) -> Any:
        """Update employee fields from a pre-dumped dict."""
        from backend.models import Employee

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            self.raise_not_found("Employee not found")

        for key, value in update_data.items():
            setattr(emp, key, value)

        await emp.save()
        logger.info("Employee updated")
        return emp

    # ====================================================================
    # PHOTO UPLOAD
    # ====================================================================

    async def upload_photo(
        self, employee_id: int, content: bytes, content_type: Optional[str] = None
    ) -> dict:
        """Validate image, save to dual storage, update employee."""
        from backend.models import Employee

        if len(content) > 5 * 1024 * 1024:
            self.raise_bad_request("File size must be less than 5MB")

        is_jpeg = len(content) >= 3 and content[:3] == b"\xff\xd8\xff"
        is_png = len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n"
        is_gif = len(content) >= 6 and content[:6] in (b"GIF87a", b"GIF89a")
        is_webp = len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"

        if not (is_jpeg or is_png or is_gif or is_webp):
            self.raise_bad_request(
                "File content does not match an allowed image format (JPEG, PNG, GIF, WebP)"
            )

        if not content_type or not content_type.startswith("image/"):
            logger.warning(
                "Photo upload for employee %s has missing/invalid content_type header (got: %s), but file content is valid",
                employee_id,
                content_type or "None",
            )

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            self.raise_not_found("Employee not found")

        # Delete old files
        for old_path in [emp.photo_path, emp.custom_photo_path]:
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        # Derive extension
        if content_type and content_type.lower() in _CONTENT_TYPE_EXT:
            ext = _CONTENT_TYPE_EXT[content_type.lower()]
        elif is_jpeg:
            ext = "jpg"
        elif is_png:
            ext = "png"
        elif is_gif:
            ext = "gif"
        else:
            ext = "webp"

        db_path, custom_path = await self.save_file_dual_storage(
            content, employee_id, emp.name, "photo", ext
        )

        emp.photo_path = db_path
        emp.custom_photo_path = custom_path
        emp.updated_at = datetime.now()
        await emp.save()

        logger.info(
            "Photo uploaded for employee_id=%s ext=%s dual_storage=%s",
            employee_id, ext, custom_path is not None,
        )
        return {
            "message": "Photo uploaded successfully",
            "db_path": db_path,
            "custom_path": custom_path,
            "dual_storage_enabled": custom_path is not None,
        }

    # ====================================================================
    # DOCUMENT UPLOAD
    # ====================================================================

    async def upload_document(
        self,
        employee_id: int,
        document_type: str,
        content: bytes,
        content_type: Optional[str] = None,
    ) -> dict:
        """Validate PDF, save to dual storage, update employee."""
        from backend.models import Employee

        if document_type not in _VALID_DOCUMENT_TYPES:
            self.raise_bad_request(
                "Invalid document type. Must be 'civil_id', 'passport', or 'visa'."
            )

        if len(content) > 10 * 1024 * 1024:
            self.raise_bad_request("File size must be less than 10MB")

        if not (len(content) >= 4 and content[:4] == b"%PDF"):
            self.raise_bad_request("File content is not a valid PDF document")

        if content_type != "application/pdf":
            logger.warning(
                "Document upload for employee %s has missing/invalid content_type header (got: %s), but file content is valid PDF",
                employee_id,
                content_type or "None",
            )

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            self.raise_not_found("Employee not found")

        db_path, custom_path = await self.save_file_dual_storage(
            content, employee_id, emp.name, document_type, "pdf"
        )

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

        for old_path in [old_db_path, old_custom_path]:
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        emp.updated_at = datetime.now()
        await emp.save()

        logger.info(
            "Document uploaded for employee_id=%s type=%s dual_storage=%s",
            employee_id, document_type, custom_path is not None,
        )
        return {
            "message": f"{document_type} document uploaded successfully",
            "db_path": db_path,
            "custom_path": custom_path,
            "dual_storage_enabled": custom_path is not None,
        }

    # ====================================================================
    # DOCUMENT DOWNLOAD
    # ====================================================================

    async def download_document(
        self,
        employee_id: int,
        document_type: str,
        raw_token: Optional[str],
    ) -> dict:
        """Authenticate token, permission-check, and resolve file path for download.

        Returns a dict with ``file_path``, ``filename``, and ``is_photo``.
        """
        from jose import jwt, JWTError
        from backend.security import SECRET_KEY, ALGORITHM
        from backend.models import Admin, Employee

        if not raw_token:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Authentication token required")

        try:
            payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if not email:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Invalid token")
            user = await Admin.find_one(Admin.email == email)
            if not user or not user.is_active:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Invalid or inactive user")
            current_user = payload
        except JWTError:
            logger.warning(
                "Invalid or expired token used for document download (employee_id=%s)",
                employee_id,
            )
            from fastapi import HTTPException
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authentication token",
            )

        emp = await Employee.find_one(Employee.uid == employee_id)
        if not emp:
            self.raise_not_found("Employee not found")

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            me = await Admin.find_one(Admin.email == current_user.get("sub"))
            if not me or emp.manager_id != me.uid:
                self.raise_forbidden("Access denied.")

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
            self.raise_bad_request("Invalid document type.")

        if file_path and not os.path.isabs(file_path):
            project_root = pathlib.Path(__file__).resolve().parent.parent.parent
            file_path = str((project_root / file_path).resolve())

        file_exists = os.path.exists(file_path) if file_path else False
        logger.debug(
            "Serving document for employee_id=%s type=%s exists=%s",
            employee_id, document_type, file_exists,
        )

        if not file_path or not file_exists:
            self.raise_not_found("Document not found")

        filename = os.path.basename(file_path)
        return {
            "file_path": file_path,
            "filename": filename,
            "is_photo": document_type == "photo",
        }
