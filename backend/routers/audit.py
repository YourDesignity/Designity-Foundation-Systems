# backend/routers/audit.py
"""
Audit Trail Router

Provides admin-only endpoints for viewing, filtering, and exporting the
audit log of all admin/manager actions.
"""

import csv
import io
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.models.audit_log import AuditLog
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Trail"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger(
    "AuditRouter",
    log_file="logs/audit_router.log",
    level=logging.DEBUG,
)


def _require_admin(current_user: dict) -> None:
    """Raise 403 if the caller is not Admin or SuperAdmin."""
    role = current_user.get("role", "")
    if role not in ("Admin", "SuperAdmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit logs are only accessible to Admin and SuperAdmin roles.",
        )


def _serialize_log(log: AuditLog) -> Dict[str, Any]:
    return {
        "id": str(log.id) if log.id else None,
        "user_id": log.user_id,
        "user_name": log.user_name,
        "user_role": log.user_role,
        "action": log.action,
        "category": log.category,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "entity_name": log.entity_name,
        "description": log.description,
        "before_data": log.before_data,
        "after_data": log.after_data,
        "ip_address": log.ip_address,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


# =============================================================================
# GET /audit-logs/ — list with filtering & pagination
# =============================================================================


@router.get("/", response_model=Dict[str, Any])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None),
    user_role: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """List audit logs with optional filtering. Admin/SuperAdmin only."""
    _require_admin(current_user)

    query: Dict[str, Any] = {}

    if category:
        query["category"] = category
    if user_role:
        query["user_role"] = user_role
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action
    if entity_type:
        query["entity_type"] = entity_type
    if date_from or date_to:
        ts: Dict[str, Any] = {}
        if date_from:
            ts["$gte"] = date_from
        if date_to:
            ts["$lte"] = date_to
        query["timestamp"] = ts
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"user_name": {"$regex": search, "$options": "i"}},
            {"entity_name": {"$regex": search, "$options": "i"}},
            {"action": {"$regex": search, "$options": "i"}},
        ]

    total = await AuditLog.find(query).count()
    skip = (page - 1) * page_size
    logs = (
        await AuditLog.find(query)
        .sort(-AuditLog.timestamp)
        .skip(skip)
        .limit(page_size)
        .to_list()
    )

    return {
        "items": [_serialize_log(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }


# =============================================================================
# GET /audit-logs/stats — statistics dashboard
# =============================================================================


@router.get("/stats", response_model=Dict[str, Any])
async def get_audit_stats(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """Return summary statistics about the audit log. Admin/SuperAdmin only."""
    _require_admin(current_user)

    query: Dict[str, Any] = {}
    if date_from or date_to:
        ts: Dict[str, Any] = {}
        if date_from:
            ts["$gte"] = date_from
        if date_to:
            ts["$lte"] = date_to
        query["timestamp"] = ts

    all_logs = await AuditLog.find(query).to_list()

    # Aggregate counts by category
    by_category: Dict[str, int] = {}
    by_user: Dict[str, int] = {}
    by_action: Dict[str, int] = {}

    for log in all_logs:
        by_category[log.category] = by_category.get(log.category, 0) + 1
        by_user[log.user_name] = by_user.get(log.user_name, 0) + 1
        by_action[log.action] = by_action.get(log.action, 0) + 1

    return {
        "total": len(all_logs),
        "by_category": by_category,
        "by_user": dict(sorted(by_user.items(), key=lambda x: -x[1])[:10]),
        "by_action": dict(sorted(by_action.items(), key=lambda x: -x[1])[:20]),
    }


# =============================================================================
# GET /audit-logs/entity/{type}/{id} — entity history
# =============================================================================


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[Dict[str, Any]])
async def get_entity_audit_history(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Return the full audit history for a specific entity. Admin/SuperAdmin only."""
    _require_admin(current_user)

    logs = (
        await AuditLog.find(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
        )
        .sort(-AuditLog.timestamp)
        .to_list()
    )

    return [_serialize_log(log) for log in logs]


# =============================================================================
# GET /audit-logs/export — CSV or JSON export
# =============================================================================


@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", pattern="^(csv|json)$"),
    category: Optional[str] = Query(None),
    user_role: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """Export audit logs as CSV or JSON. Admin/SuperAdmin only."""
    _require_admin(current_user)

    query: Dict[str, Any] = {}
    if category:
        query["category"] = category
    if user_role:
        query["user_role"] = user_role
    if date_from or date_to:
        ts: Dict[str, Any] = {}
        if date_from:
            ts["$gte"] = date_from
        if date_to:
            ts["$lte"] = date_to
        query["timestamp"] = ts

    logs = await AuditLog.find(query).sort(-AuditLog.timestamp).to_list()
    serialized = [_serialize_log(log) for log in logs]

    if format == "json":
        import json

        content = json.dumps(serialized, indent=2, default=str)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )

    # CSV export
    output = io.StringIO()
    fieldnames = [
        "timestamp",
        "user_name",
        "user_role",
        "action",
        "category",
        "entity_type",
        "entity_id",
        "entity_name",
        "description",
        "ip_address",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in serialized:
        writer.writerow({k: row.get(k, "") for k in fieldnames})

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
