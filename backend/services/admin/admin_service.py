"""Service layer for admin authentication and account operations."""

import logging
from datetime import timedelta
from typing import Any, Optional

from fastapi import HTTPException, status

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class AdminService(BaseService):
    """Business logic for admin lifecycle and authentication."""

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
        password_to_verify = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")

        if not user or not verify_password(password_to_verify, user.hashed_password):
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
