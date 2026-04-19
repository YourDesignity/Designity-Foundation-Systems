# File: backend/security.py

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# Import the MongoDB Model
from backend.models import Admin

# Import RBAC permission helpers
from backend.config.permissions import has_permission as _rbac_has_permission

# Load environment variables
load_dotenv()

# =============================================================================
# 1. CONFIGURATION
# =============================================================================

# 🚨 SECURITY FIX: No longer hardcoded. Reads from .env or defaults to a safe dev key.
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_to_a_long_random_string_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# =============================================================================
# 2. PASSWORD UTILITIES
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# =============================================================================
# 3. JWT UTILITIES
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT token containing the user's data (sub, role, perms).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# =============================================================================
# 4. AUTHENTICATION DEPENDENCY (The Guard)
# =============================================================================

async def get_current_active_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Validates the JWT and checks against MongoDB if the user is still active.
    Returns the Token Payload (which contains role/perms) to keep downstream logic simple.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decode the Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
        # 2. Check MongoDB (Is the user still active?)
        # This prevents banned users from using old tokens.
        user = await Admin.find_one(Admin.email == email)
        
        if user is None:
            raise credentials_exception
            
        if not user.is_active:
            raise HTTPException(status_code=400, detail="User account is inactive")

        # 3. Return the payload
        # We return the payload (not the user object) because the payload 
        # already has 'perms' and 'sites' baked in, which the Routers expect.
        return payload

    except JWTError:
        raise credentials_exception

# =============================================================================
# 5. PERMISSION CHECKER
# =============================================================================

# Roles that have implicit access to all permissions (bypass per-permission checks)
PRIVILEGED_ROLES = {"SuperAdmin", "Admin"}

def require_permission(required_permission: str):
    """
    Factory that creates a dependency to check if the current user's role
    has the specified permission, using the centralised RBAC config.

    Usage:
        @router.get("/finance/data", dependencies=[Depends(require_permission("finance:view"))])
        async def get_finance_data():
            ...
    """
    async def permission_checker(current_user: dict = Depends(get_current_active_user)) -> dict:
        user_role = current_user.get("role")
        if not _rbac_has_permission(user_role, required_permission):
            # Fallback: honour legacy per-token perms array for backward compatibility
            user_permissions = current_user.get("perms", [])
            if required_permission not in user_permissions and "all" not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{required_permission}' required. Access denied."
                )
        return current_user

    return permission_checker


def check_user_permission(current_user: dict, permission: str) -> bool:
    """
    Helper to check if the current user object has a specific permission.
    Uses the centralised RBAC config first; falls back to the token's perms array.

    Args:
        current_user: JWT payload dict containing at least 'role'
        permission:   Permission string to check (e.g. "finance:view")

    Returns:
        True if the user has the permission, False otherwise
    """
    user_role = current_user.get("role")
    if _rbac_has_permission(user_role, permission):
        return True
    # Legacy fallback
    user_permissions = current_user.get("perms", [])
    return permission in user_permissions or "all" in user_permissions
