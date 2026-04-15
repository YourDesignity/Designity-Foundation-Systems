# backend/routers/manager_sites.py

import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.models import Admin, Site, Employee, Attendance, EmployeeAssignment
from backend.database import get_next_uid
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/manager-sites",
    tags=["Manager Site Management"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("ManagerSitesRouter", log_file="logs/manager_sites_router.log", level=logging.DEBUG)


# ===== SCHEMAS =====

class AttendanceRecord(BaseModel):
    employee_uid: int
    status: str  # "Present" | "Absent" | "Late" | "Half Day" | "On Leave"
    shift: Optional[str] = "Morning"
    overtime_hours: Optional[int] = 0
    is_substitute: bool = False
    replacing_employee_id: Optional[int] = None
    leave_type: Optional[str] = None
    leave_reason: Optional[str] = None
    substitute_requested: bool = False
    notes: Optional[str] = None

class BulkAttendanceRequest(BaseModel):
    site_id: int
    date: str  # YYYY-MM-DD
    records: List[AttendanceRecord]


# ===== ENDPOINTS =====

@router.get("/{manager_id}/sites")
async def get_manager_sites(
    manager_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all sites managed by a specific manager."""
    # Allow the manager to view their own sites, or Admins to view any manager's sites
    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.uid != manager_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    manager = await Admin.find_one(Admin.uid == manager_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")

    sites = await Site.find(Site.assigned_manager_id == manager_id).to_list()

    site_summaries = []
    for site in sites:
        assignments = await EmployeeAssignment.find(
            EmployeeAssignment.site_id == site.uid,
            EmployeeAssignment.status == "Active"
        ).count()

        site_dict = site.model_dump(mode='json')
        site_dict["active_employees"] = assignments
        site_dict["is_understaffed"] = site.is_understaffed
        site_dict["headcount_shortage"] = site.headcount_shortage
        site_summaries.append(site_dict)

    logger.info(f"Manager {manager_id} has {len(sites)} sites")
    return {
        "manager_id": manager_id,
        "manager_name": manager.full_name,
        "total_sites": len(sites),
        "sites": site_summaries
    }


@router.get("/{manager_id}/sites/{site_id}/employees")
async def get_managed_site_employees(
    manager_id: int,
    site_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all employees at a site managed by this manager."""
    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.uid != manager_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if site.assigned_manager_id != manager_id and current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="This manager is not assigned to this site")

    assignments = await EmployeeAssignment.find(
        EmployeeAssignment.site_id == site_id,
        EmployeeAssignment.status == "Active"
    ).to_list()

    employees = []
    for assignment in assignments:
        emp = await Employee.find_one(Employee.uid == assignment.employee_id)
        if emp:
            employees.append({
                "employee": emp.model_dump(mode='json'),
                "assignment": assignment.model_dump(mode='json')
            })

    # Include substitutes
    substitutes = []
    for uid in site.active_substitute_uids:
        emp = await Employee.find_one(Employee.uid == uid)
        if emp:
            substitutes.append(emp.model_dump(mode='json'))

    return {
        "site": site.model_dump(mode='json'),
        "company_employees": employees,
        "substitutes": substitutes,
        "total_workers": len(employees) + len(substitutes),
        "required_workers": site.required_workers,
        "is_understaffed": site.is_understaffed,
    }


@router.post("/{manager_id}/sites/{site_id}/attendance", status_code=status.HTTP_201_CREATED)
async def record_site_attendance(
    manager_id: int,
    site_id: int,
    request: BulkAttendanceRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Record attendance for all employees at a managed site."""
    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.uid != manager_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    site = await Site.find_one(Site.uid == site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if site.assigned_manager_id != manager_id and current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="This manager is not assigned to this site")

    manager = await Admin.find_one(Admin.uid == manager_id)

    created = []
    updated = []
    failed = []

    for record in request.records:
        try:
            employee = await Employee.find_one(Employee.uid == record.employee_uid)
            if not employee:
                failed.append({"employee_uid": record.employee_uid, "reason": "Employee not found"})
                continue

            # Check if attendance already recorded for this date
            existing = await Attendance.find_one(
                Attendance.employee_uid == record.employee_uid,
                Attendance.date == request.date,
                Attendance.site_uid == site_id
            )

            if existing:
                # Update existing record
                existing.status = record.status
                existing.shift = record.shift
                existing.overtime_hours = record.overtime_hours
                # is_replacement is the legacy field; is_substitute is the new field.
                # Both are set to ensure backward compatibility with old queries.
                existing.is_replacement = record.is_substitute
                existing.replacing_employee_id = record.replacing_employee_id
                existing.replacement_reason = record.leave_reason
                existing.recorded_by_manager_id = manager_id
                existing.recorded_by_manager_name = manager.full_name if manager else None
                existing.is_substitute = record.is_substitute
                existing.leave_type = record.leave_type
                existing.leave_reason = record.leave_reason
                existing.substitute_requested = record.substitute_requested
                existing.notes = record.notes
                existing.recorded_at = datetime.now()
                await existing.save()
                updated.append(existing.model_dump(mode='json'))
            else:
                new_uid = await get_next_uid("attendance")
                attendance = Attendance(
                    uid=new_uid,
                    employee_uid=record.employee_uid,
                    site_uid=site_id,
                    date=request.date,
                    status=record.status,
                    shift=record.shift,
                    overtime_hours=record.overtime_hours,
                    # is_replacement is legacy; is_substitute is the new field.
                    is_replacement=record.is_substitute,
                    replacing_employee_id=record.replacing_employee_id,
                    replacement_reason=record.leave_reason,
                    recorded_by_manager_id=manager_id,
                    recorded_by_manager_name=manager.full_name if manager else None,
                    is_substitute=record.is_substitute,
                    leave_type=record.leave_type,
                    leave_reason=record.leave_reason,
                    substitute_requested=record.substitute_requested,
                    notes=record.notes,
                    recorded_at=datetime.now()
                )
                await attendance.insert()
                created.append(attendance.model_dump(mode='json'))

        except Exception as e:
            logger.error(f"Error recording attendance for employee {record.employee_uid}: {e}")
            failed.append({"employee_uid": record.employee_uid, "reason": "Failed to record attendance"})

    logger.info(f"Attendance recorded: {len(created)} new, {len(updated)} updated, {len(failed)} failed for site {site_id}")

    return {
        "message": f"Attendance recorded: {len(created)} new, {len(updated)} updated",
        "site_id": site_id,
        "date": request.date,
        "created_count": len(created),
        "updated_count": len(updated),
        "failed_count": len(failed),
        "records": created + updated,
        "failures": failed
    }


@router.get("/{manager_id}/sites/{site_id}/attendance")
async def get_site_attendance(
    manager_id: int,
    site_id: int,
    attendance_date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get attendance records for a site. Optionally filter by date."""
    if current_user.get("role") == "Site Manager":
        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.uid != manager_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    filters = [Attendance.site_uid == site_id]
    if attendance_date:
        filters.append(Attendance.date == attendance_date)

    records = await Attendance.find(*filters).sort("-date").to_list()

    return {
        "site_id": site_id,
        "date": attendance_date,
        "total_records": len(records),
        "records": [r.model_dump(mode='json') for r in records]
    }
