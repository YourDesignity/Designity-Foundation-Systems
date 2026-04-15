# backend/routers/workforce_analytics.py

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from backend.models import Employee, Site, Project, EmployeeAssignment, TemporaryAssignment
from backend.security import get_current_active_user
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/workforce",
    tags=["Workforce Analytics"],
    dependencies=[Depends(get_current_active_user)],
)

logger = setup_logger("WorkforceAnalyticsRouter", log_file="logs/workforce_analytics.log", level=logging.DEBUG)


@router.get("/allocation")
async def get_workforce_allocation():
    """
    Returns workforce allocation data grouped by project/site.
    Includes available employees, assignments by project, and active external workers.
    """
    # --- Available employees ---
    available_emps = await Employee.find(
        Employee.status == "Active",
        Employee.employee_type == "Company",
        Employee.is_currently_assigned == False,
    ).to_list()

    available_list = []
    for e in available_emps:
        available_list.append({
            "employee_id": e.uid,
            "name": e.name,
            "designation": e.designation,
            "availability_status": e.availability_status,
            "photo_path": e.photo_path,
        })

    # --- Assignments grouped by project ---
    all_projects = await Project.find(Project.status == "Active").to_list()
    assignments_by_project = {}

    for project in all_projects:
        sites = await Site.find(Site.project_id == project.uid, Site.status == "Active").to_list()
        site_data = []
        for site in sites:
            # Get active assignments for this site
            assignments = await EmployeeAssignment.find(
                EmployeeAssignment.site_id == site.uid,
                EmployeeAssignment.status == "Active",
            ).to_list()

            emp_list = []
            for a in assignments:
                emp_list.append({
                    "assignment_id": a.uid,
                    "employee_id": a.employee_id,
                    "employee_name": a.employee_name,
                    "employee_type": a.employee_type,
                    "designation": a.employee_designation,
                    "assignment_start": a.assignment_start.isoformat() if a.assignment_start else None,
                })

            site_data.append({
                "site_id": site.uid,
                "site_name": site.name,
                "site_code": site.site_code,
                "required_workers": site.required_workers,
                "assigned_workers": site.assigned_workers,
                "fill_pct": round(
                    (site.assigned_workers / site.required_workers * 100)
                    if site.required_workers else 0, 1
                ),
                "employees": emp_list,
            })

        assignments_by_project[str(project.uid)] = {
            "project_id": project.uid,
            "project_code": project.project_code,
            "project_name": project.project_name,
            "client_name": project.client_name,
            "sites": site_data,
            "total_assigned": project.total_assigned_employees,
        }

    # --- Active external workers ---
    active_temp = await TemporaryAssignment.find(
        TemporaryAssignment.status == "Active"
    ).to_list()

    external_list = []
    for t in active_temp:
        external_list.append({
            "assignment_id": t.uid,
            "employee_id": t.employee_id,
            "employee_name": t.employee_name,
            "designation": t.employee_designation,
            "site_id": t.site_id,
            "site_name": t.site_name,
            "start_date": t.start_date.isoformat() if t.start_date else None,
            "end_date": t.end_date.isoformat() if t.end_date else None,
            "rate_type": t.rate_type,
            "daily_rate": t.daily_rate,
        })

    # --- Utilization summary ---
    total_company = await Employee.find(
        Employee.status == "Active",
        Employee.employee_type == "Company",
    ).count()
    assigned_company = await Employee.find(
        Employee.status == "Active",
        Employee.employee_type == "Company",
        Employee.is_currently_assigned == True,
    ).count()
    utilization_pct = round(
        (assigned_company / total_company * 100) if total_company else 0, 1
    )

    return {
        "available_employees": available_list,
        "assignments_by_project": assignments_by_project,
        "external_workers": external_list,
        "summary": {
            "total_company_employees": total_company,
            "assigned_company_employees": assigned_company,
            "available_company_employees": total_company - assigned_company,
            "active_external_workers": len(external_list),
            "utilization_percentage": utilization_pct,
        },
    }


@router.get("/utilization")
async def get_workforce_utilization():
    """
    Returns workforce utilization data for charts (pie chart, bar chart, trend).
    """
    today = datetime.now()
    week_ago = today - timedelta(days=7)

    total_company = await Employee.find(
        Employee.status == "Active",
        Employee.employee_type == "Company",
    ).count()
    assigned_company = await Employee.find(
        Employee.status == "Active",
        Employee.employee_type == "Company",
        Employee.is_currently_assigned == True,
    ).count()
    active_external = await TemporaryAssignment.find(
        TemporaryAssignment.status == "Active"
    ).count()

    available_count = total_company - assigned_company

    # --- Per-project employee count ---
    projects = await Project.find(Project.status == "Active").to_list()
    per_project = []
    for p in projects:
        per_project.append({
            "project_name": p.project_code,
            "full_name": p.project_name,
            "assigned_employees": p.total_assigned_employees,
        })
    per_project.sort(key=lambda x: x["assigned_employees"], reverse=True)

    # --- Recent assignments (last 7 days) ---
    recent_assignments = await EmployeeAssignment.find(
        EmployeeAssignment.assigned_date >= week_ago,
    ).to_list()
    recent_list = []
    for a in recent_assignments:
        recent_list.append({
            "employee_name": a.employee_name,
            "site_name": a.site_name,
            "project_name": a.project_name,
            "assigned_date": a.assigned_date.isoformat() if a.assigned_date else None,
            "status": a.status,
        })

    return {
        "pie_chart": {
            "available": available_count,
            "assigned_company": assigned_company,
            "assigned_external": active_external,
        },
        "bar_chart": per_project,
        "recent_assignments": recent_list,
    }
