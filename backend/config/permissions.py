"""
Role-Based Access Control (RBAC) Configuration

This file defines ALL permissions in the system.
Changes to permissions require code review and deployment for security.

Permission Format: "resource:action"
Examples: "finance:view", "employees:edit", "projects:delete"
"""

# ─── PERMISSION DEFINITIONS ───────────────────────────────────────────────────

# Complete list of all permissions in the system
ALL_PERMISSIONS = {
    # Dashboard & Analytics
    "dashboard:view",
    "analytics:view",
    "workforce:view",

    # Finance (RESTRICTED)
    "finance:view",
    "finance:export",

    # Employee Management
    "employees:view",
    "employees:create",
    "employees:edit",
    "employees:delete",
    "employees:assign",

    # Manager Management
    "managers:view",
    "managers:create",
    "managers:edit",
    "managers:delete",

    # Admin Management (SUPER RESTRICTED)
    "admins:view",
    "admins:create",
    "admins:edit",
    "admins:delete",

    # Projects & Contracts
    "projects:view",
    "projects:create",
    "projects:edit",
    "projects:delete",
    "contracts:view",
    "contracts:create",
    "contracts:edit",
    "contracts:delete",

    # Sites
    "sites:view",
    "sites:create",
    "sites:edit",
    "sites:delete",
    "sites:assign-workers",

    # Attendance & Payroll
    "attendance:view",
    "attendance:edit",
    "payslips:view",
    "payslips:generate",
    "overtime:view",
    "overtime:approve",
    "deductions:view",
    "deductions:manage",

    # Operations
    "inventory:view",
    "inventory:edit",
    "vehicles:view",
    "vehicles:edit",
    "vehicles:create",
    "vehicles:delete",
    "duty-list:view",
    "duty-list:manage",

    # Communication
    "messages:view",
    "messages:send",
    "messages:broadcast",
    "messages:view-all",

    # Settings
    "settings:view",
    "settings:edit",

    # Profile
    "my-profile:view",
    "my-profile:edit",
    "my-attendance:view",
    "my-attendance:edit",
}

# ─── ROLE PERMISSION MAPPINGS ─────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "SuperAdmin": [
        "*"  # Wildcard: Has ALL permissions
    ],

    "Admin": [
        # Dashboard & Analytics
        "dashboard:view",
        "analytics:view",
        "workforce:view",

        # Finance (GRANTED TO ADMIN)
        "finance:view",
        "finance:export",

        # Employee Management
        "employees:view",
        "employees:create",
        "employees:edit",
        # NOTE: NO "employees:delete" - only SuperAdmin can delete
        "employees:assign",

        # Manager Management
        "managers:view",
        "managers:create",
        "managers:edit",
        # NOTE: NO "managers:delete" - only SuperAdmin

        # Admin Management (view only)
        "admins:view",

        # Projects & Contracts
        "projects:view",
        "projects:create",
        "projects:edit",
        "projects:delete",
        "contracts:view",
        "contracts:create",
        "contracts:edit",
        "contracts:delete",

        # Sites
        "sites:view",
        "sites:create",
        "sites:edit",
        "sites:delete",
        "sites:assign-workers",

        # Attendance & Payroll
        "attendance:view",
        "attendance:edit",
        "payslips:view",
        "payslips:generate",
        "overtime:view",
        "overtime:approve",
        "deductions:view",
        "deductions:manage",

        # Operations
        "inventory:view",
        "inventory:edit",
        "vehicles:view",
        "vehicles:edit",
        "vehicles:create",
        "duty-list:view",
        "duty-list:manage",

        # Communication
        "messages:view",
        "messages:send",
        "messages:broadcast",
        "messages:view-all",

        # Settings (limited)
        "settings:view",

        # Profile
        "my-profile:view",
        "my-profile:edit",
        "my-attendance:view",
    ],

    "Site Manager": [
        # Dashboard (read-only)
        "dashboard:view",

        # Employees (view only)
        "employees:view",

        # Attendance (for their site/team)
        "attendance:view",
        "attendance:edit",

        # Communication
        "messages:view",
        "messages:send",  # Can send but not broadcast

        # Profile
        "my-profile:view",
        "my-profile:edit",
        "my-attendance:view",
        "my-attendance:edit",

        # Their assigned site
        "sites:view",
    ],
}

# ─── PERMISSION UTILITIES ─────────────────────────────────────────────────────


def get_role_permissions(role: str) -> list[str]:
    """
    Get all permissions for a given role.

    Args:
        role: User role ("SuperAdmin", "Admin", "Site Manager")

    Returns:
        List of permission strings
    """
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user_role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        user_role: User's role
        permission: Permission to check (e.g., "finance:view")

    Returns:
        True if role has permission, False otherwise
    """
    perms = get_role_permissions(user_role)

    # SuperAdmin has wildcard access
    if "*" in perms:
        return True

    return permission in perms


def has_any_permission(user_role: str, permissions: list[str]) -> bool:
    """Check if role has ANY of the specified permissions."""
    return any(has_permission(user_role, perm) for perm in permissions)


def has_all_permissions(user_role: str, permissions: list[str]) -> bool:
    """Check if role has ALL of the specified permissions."""
    return all(has_permission(user_role, perm) for perm in permissions)


def get_user_permissions(user_role: str) -> list[str]:
    """
    Get complete list of permissions for a user role.
    Expands wildcard if present.
    """
    perms = get_role_permissions(user_role)

    if "*" in perms:
        return list(ALL_PERMISSIONS)

    return perms
