"""Service layer for admin authentication and account operations."""

import logging
import os
from datetime import timedelta
from typing import Any, Optional

from fastapi import HTTPException, status

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class AdminService(BaseService):
    """Business logic for admin lifecycle and authentication."""

    @staticmethod
    def _validate_bcrypt_password_length(password: str) -> None:
        """Reject passwords exceeding bcrypt's 72-byte effective input limit."""
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password exceeds bcrypt limit of 72 UTF-8 bytes")

    async def create_admin(self, payload: Any, current_user: Optional[dict] = None):
        """
        Create a new admin account.

        Validations:
        - Email must be unique
        - Role must be resolvable from role_id/role
        - Caller permission must allow creating target role (when current_user is provided)

        Args:
            payload: Admin creation payload (pydantic model or dict)
            current_user: Authenticated caller payload

        Returns:
            Created Admin document

        Raises:
            HTTPException 400: Invalid role or duplicate email
            HTTPException 403: Permission denied
        """
        from backend.core.config_loader import RoleConfig
        from backend.models import Admin
        from backend.security import PRIVILEGED_ROLES, get_password_hash

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

        email = data.get("email")
        if not email:
            self.raise_bad_request("Email is required")

        existing = await Admin.find_one(Admin.email == email)
        if existing:
            self.raise_bad_request("Email already registered")

        target_role_name = data.get("role")
        role_id = data.get("role_id")
        if role_id is not None:
            target_role_config = RoleConfig.get_role_by_id(role_id)
            if not target_role_config:
                self.raise_bad_request("Invalid Role ID")
            target_role_name = target_role_config["db_name"]
            default_perms = target_role_config["permissions"]
        elif target_role_name:
            target_role_config = RoleConfig.get_role_by_name(target_role_name)
            default_perms = target_role_config["permissions"] if target_role_config else data.get("permissions", [])
        else:
            self.raise_bad_request("Role is required")

        if current_user:
            user_role = current_user.get("role")
            if user_role not in PRIVILEGED_ROLES:
                required_perm = "admin:create:manager" if target_role_name == "Site Manager" else "admin:create:admin"
                user_perms = current_user.get("perms", [])
                if required_perm not in user_perms:
                    self.raise_forbidden(f"Missing permission: {required_perm}")

        password = data.get("password")
        if not password:
            self.raise_bad_request("Password is required")
        try:
            self._validate_bcrypt_password_length(password)
        except ValueError as exc:
            self.raise_bad_request(str(exc))

        new_uid = await self.get_next_uid("admins")
        new_admin = Admin(
            uid=new_uid,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=data.get("full_name", ""),
            designation=data.get("designation", ""),
            role=target_role_name,
            permissions=default_perms,
            assigned_site_uids=data.get("assigned_site_uids", []),
            has_manager_profile=bool(data.get("has_manager_profile", False)),
            phone=data.get("phone"),
        )
        await new_admin.insert()
        logger.info("Admin created: %s (ID: %s)", new_admin.email, new_uid)
        return new_admin

    async def get_admin_by_id(self, admin_id: int):
        """
        Get admin by UID.

        Validations:
        - Admin must exist

        Args:
            admin_id: Admin UID

        Returns:
            Admin document

        Raises:
            HTTPException 404: Admin not found
        """
        from backend.models import Admin

        admin = await Admin.find_one(Admin.uid == admin_id)
        if not admin:
            self.raise_not_found("Admin not found")
        return admin

    async def authenticate_admin(self, username: str, password: str, include_user: bool = False) -> dict:
        """
        Authenticate admin credentials and issue JWT.

        Validations:
        - Email/password must match
        - User must be active

        Args:
            username: Admin email
            password: Plain text password
            include_user: Include lightweight user payload in response

        Returns:
            Token response payload

        Raises:
            HTTPException 401: Invalid credentials
            HTTPException 400: Inactive user
        """
        from backend import security
        from backend.models import Admin
        from backend.security import verify_password

        user = await Admin.find_one(Admin.email == username)
        try:
            self._validate_bcrypt_password_length(password)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            self.raise_bad_request("User is inactive")

        power_level = {"SuperAdmin": 100, "Admin": 50, "Site Manager": 20}.get(user.role, 0)
        token_data = {
            "id": user.uid,
            "sub": user.email,
            "role": user.role,
            "power": power_level,
            "perms": user.permissions or [],
            "sites": user.assigned_site_uids or [],
            "full_name": user.full_name,
            "profile_photo": user.profile_photo,
        }
        access_token = security.create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        response = {"access_token": access_token, "token_type": "bearer"}
        if include_user:
            response["user"] = {
                "uid": user.uid,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
            }
        return response

    async def change_password(
        self,
        admin_id: int,
        new_password: str,
        current_password: Optional[str] = None,
    ) -> dict:
        """
        Change admin password.

        Validations:
        - Admin must exist
        - Current password must match when provided

        Args:
            admin_id: Admin UID
            new_password: New plain text password
            current_password: Existing password (optional)

        Returns:
            Success payload

        Raises:
            HTTPException 400: Invalid current password
            HTTPException 404: Admin not found
        """
        from backend.security import get_password_hash, verify_password

        admin = await self.get_admin_by_id(admin_id)

        if current_password and not verify_password(current_password, admin.hashed_password):
            self.raise_bad_request("Current password is incorrect")
        try:
            self._validate_bcrypt_password_length(new_password)
        except ValueError as exc:
            self.raise_bad_request(str(exc))

        admin.hashed_password = get_password_hash(new_password)
        await admin.save()
        logger.info("Password changed for admin ID %s", admin_id)
        return {"message": "Password updated successfully"}

    def check_permission(self, current_user: dict, permission: str) -> bool:
        """
        Check whether a user has a specific permission.

        Validations:
        - Uses centralized RBAC checks with legacy token-permission fallback

        Args:
            current_user: Authenticated user payload
            permission: Permission key

        Returns:
            True when allowed, otherwise False
        """
        from backend.security import check_user_permission

        return check_user_permission(current_user, permission)

    async def get_all_admins(self) -> list[dict]:
        """Return all admins with dynamic role metadata."""
        from backend.core.config_loader import RoleConfig
        from backend.models import Admin

        admins = await Admin.find_all().to_list()
        results: list[dict] = []
        for admin in admins:
            role_config = RoleConfig.get_role_by_name(admin.role)
            role_id = role_config["legacy_id"] if role_config else 0
            results.append(
                {
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
                        "description": "Managed by Config",
                    },
                }
            )
        return results

    async def get_all_managers(self, current_user: dict) -> list[dict]:
        """Return active site-manager accounts."""
        from backend.models import Admin

        user_role = current_user.get("role")
        if user_role not in ["SuperAdmin", "Admin", "Site Manager"]:
            self.raise_forbidden("Forbidden")

        managers = await Admin.find(Admin.role == "Site Manager", Admin.is_active == True).to_list()
        return [m.model_dump(mode="json") for m in managers]

    async def get_my_profile(self, admin_id: int) -> dict:
        """Return self profile details."""
        from backend.models import Admin

        admin = await Admin.find_one(Admin.uid == admin_id)
        if not admin:
            self.raise_not_found("Profile not found")

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

    async def update_my_profile(self, admin_id: int, payload: Any) -> dict:
        """Update self profile fields."""
        from backend.models import Admin

        admin = await Admin.find_one(Admin.uid == admin_id)
        if not admin:
            self.raise_not_found("Profile not found")

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        if "full_name" in data:
            admin.full_name = data["full_name"]
        if "designation" in data:
            admin.designation = data["designation"]
        if "phone" in data:
            admin.phone = data["phone"]

        await admin.save()
        return {"message": "Profile updated successfully"}

    async def upload_admin_photo(self, admin_id: int, content: bytes, upload_dir: str) -> dict:
        """Validate and save admin profile photo."""
        from backend.models import Admin

        if len(content) > 5 * 1024 * 1024:
            self.raise_bad_request("File size must be less than 5 MB")

        is_jpeg = len(content) >= 3 and content[:3] == b"\xff\xd8\xff"
        is_png = len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n"
        if not (is_jpeg or is_png):
            self.raise_bad_request("Only JPEG and PNG images are allowed")

        ext = "png" if is_png else "jpg"
        safe_admin_id = int(admin_id)
        filename = f"admin_{safe_admin_id}.{ext}"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)

        admin = await Admin.find_one(Admin.uid == safe_admin_id)
        if not admin:
            self.raise_not_found("Admin not found")

        admin.profile_photo = f"/uploads/admin_photos/{filename}"
        await admin.save()
        return {"message": "Photo uploaded successfully", "photo_url": admin.profile_photo}

    async def update_admin(self, admin_id: int, admin_update: Any, current_user: dict) -> dict:
        """Update admin details with role-based protection."""
        from backend.core.config_loader import RoleConfig
        from backend.models import Admin

        admin = await Admin.find_one(Admin.uid == admin_id)
        if not admin:
            self.raise_not_found("Admin not found")

        if admin.role and admin.role.lower() == "superadmin" and current_user.get("role") != "SuperAdmin":
            self.raise_forbidden("Only SuperAdmins can edit SuperAdmin accounts")

        update_data = admin_update.model_dump(exclude_unset=True) if hasattr(admin_update, "model_dump") else dict(admin_update)
        if "full_name" in update_data:
            admin.full_name = update_data["full_name"]
        if "designation" in update_data:
            admin.designation = update_data["designation"]
        if "is_active" in update_data:
            admin.is_active = update_data["is_active"]
        if "phone" in update_data:
            admin.phone = update_data["phone"]
        if "email" in update_data:
            admin.email = update_data["email"]

        role_id = update_data.get("role_id")
        if role_id:
            new_role_config = RoleConfig.get_role_by_id(role_id)
            if new_role_config:
                admin.role = new_role_config["db_name"]
                admin.permissions = new_role_config["permissions"]

        await admin.save()
        return {"status": "success"}

    async def delete_admin(self, admin_id: int, current_user_id: int) -> None:
        """Delete admin account with self-delete guard."""
        from backend.models import Admin

        admin = await Admin.find_one(Admin.uid == admin_id)
        if not admin:
            self.raise_not_found("Admin not found")
        if admin_id == current_user_id:
            self.raise_forbidden("You cannot delete your own account")
        await admin.delete()
