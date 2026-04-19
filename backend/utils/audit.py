"""Audit logging helpers for tracking admin/manager actions."""

from datetime import datetime
from typing import Any, Dict, Optional

from backend.models.audit_log import AuditLog


async def log_audit(
    *,
    user: dict,
    action: str,
    category: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    description: str = "",
    before_data: Optional[Dict[str, Any]] = None,
    after_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Write an audit log entry.

    This is the core logging function used by all helpers below.
    It is designed to be called with keyword arguments for clarity.
    """
    entry = AuditLog(
        user_id=user.get("uid") or user.get("id") or 0,
        user_name=user.get("name") or user.get("sub") or "Unknown",
        user_role=user.get("role") or "Unknown",
        action=action,
        category=category,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        entity_name=entity_name,
        description=description,
        before_data=before_data,
        after_data=after_data,
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.now(),
    )
    await entry.insert()
    return entry


async def audit_create(
    *,
    user: dict,
    category: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Log an entity creation action."""
    description = f"{user.get('name', 'Unknown')} created {entity_type}"
    if entity_name:
        description += f" '{entity_name}'"
    if entity_id:
        description += f" (ID: {entity_id})"
    return await log_audit(
        user=user,
        action=f"{entity_type}_created",
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
        after_data=data,
        ip_address=ip_address,
    )


async def audit_update(
    *,
    user: dict,
    category: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Log an entity update action with before/after snapshots."""
    description = f"{user.get('name', 'Unknown')} updated {entity_type}"
    if entity_name:
        description += f" '{entity_name}'"
    if entity_id:
        description += f" (ID: {entity_id})"
    return await log_audit(
        user=user,
        action=f"{entity_type}_updated",
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
        before_data=before,
        after_data=after,
        ip_address=ip_address,
    )


async def audit_delete(
    *,
    user: dict,
    category: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Log an entity deletion action."""
    description = f"{user.get('name', 'Unknown')} deleted {entity_type}"
    if entity_name:
        description += f" '{entity_name}'"
    if entity_id:
        description += f" (ID: {entity_id})"
    return await log_audit(
        user=user,
        action=f"{entity_type}_deleted",
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
        before_data=data,
        ip_address=ip_address,
    )
