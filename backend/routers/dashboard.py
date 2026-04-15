# backend/routers/dashboard.py

import os
import psutil
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from backend.security import get_current_active_user, require_permission
from backend.models import Employee, Admin, Site, Attendance, Schedule, Project, Contract, TemporaryAssignment, EmployeeAssignment

router = APIRouter(
    prefix="/dashboard",
    tags=["System Dashboard"]
)

@router.get("/stats")
async def get_system_stats():
    """
    Returns counts of all major collections for the UI cards.
    """
    return {
        "employees": await Employee.count(),
        "admins": await Admin.count(),
        "sites": await Site.count(),
        "attendance_records": await Attendance.count(),
        "schedules": await Schedule.count()
    }

@router.get("/system_health")
async def get_system_health():
    """
    Returns Server RAM/CPU usage.
    """
    process = psutil.Process(os.getpid())
    return {
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage_mb": process.memory_info().rss / 1024 / 1024,
        "total_ram_percent": psutil.virtual_memory().percent
    }

@router.get("/schema_graph")
async def get_schema_visualization():
    """
    Defines the nodes and edges for the Graph.
    """
    # Nodes: The Collections
    nodes = [
        {"id": 1, "label": "Employees", "color": "#4CAF50"},
        {"id": 2, "label": "Sites", "color": "#2196F3"},
        {"id": 3, "label": "Admins\n(Managers)", "color": "#FF9800"},
        {"id": 4, "label": "Attendance", "color": "#9C27B0"},
        {"id": 5, "label": "Schedules", "color": "#607D8B"},
    ]
    
    # Edges: The 'uid' Links
    edges = [
        {"from": 3, "to": 2, "label": "manages", "arrows": "to"},    # Admin -> Site
        {"from": 3, "to": 1, "label": "manages", "arrows": "to"},    # Admin -> Employee
        {"from": 1, "to": 4, "label": "logs", "arrows": "to"},       # Employee -> Attendance
        {"from": 2, "to": 4, "label": "location", "arrows": "to"},   # Site -> Attendance
        {"from": 1, "to": 5, "label": "assigned", "arrows": "to"},   # Employee -> Schedule
        {"from": 2, "to": 5, "label": "location", "arrows": "to"},   # Site -> Schedule
    ]
    
    return {"nodes": nodes, "edges": edges}

@router.get("/logs/live")
async def get_live_logs():
    """
    Reads the last 50 lines of the main app log.
    """
    log_file = "logs/app_main.log"
    if not os.path.exists(log_file):
        return ["Log file not created yet."]
    
    with open(log_file, "r") as f:
        # Read all lines and take the last 50
        lines = f.readlines()
        return lines[-50:]


@router.get("/summary", dependencies=[Depends(get_current_active_user)])
async def get_dashboard_summary():
    """
    Returns a comprehensive dashboard summary for the Phase 6 overview page.
    Includes project stats, workforce counts, contract alerts, and workforce gaps.
    """
    today = datetime.now()
    total_employees = await Employee.find(Employee.status == "Active").count()
    available_employees = await Employee.find(
        Employee.status == "Active",
        Employee.is_currently_assigned == False
    ).count()
    assigned_employees = total_employees - available_employees

    all_projects = await Project.find().to_list()
    total_projects = len(all_projects)
    active_projects = sum(1 for p in all_projects if p.status == "Active")
    completed_projects = sum(1 for p in all_projects if p.status == "Completed")
    on_hold_projects = sum(1 for p in all_projects if p.status == "On Hold")

    all_sites = await Site.find().to_list()
    total_sites = len(all_sites)

    active_external = await TemporaryAssignment.find(
        TemporaryAssignment.status == "Active"
    ).count()

    # --- Contract expiry alerts ---
    all_contracts = await Contract.find(Contract.status == "Active").to_list()
    expiring_soon = []
    for c in all_contracts:
        if c.end_date:
            days_left = (c.end_date - today).days
            if days_left <= 30:
                expiring_soon.append({
                    "contract_id": c.uid,
                    "contract_code": c.contract_code,
                    "contract_name": c.contract_name,
                    "project_name": c.project_name,
                    "end_date": c.end_date.isoformat(),
                    "days_remaining": days_left,
                    "alert_level": "danger" if days_left <= 7 else "warning",
                })
    expiring_soon.sort(key=lambda x: x["days_remaining"])

    # --- Workforce gaps ---
    workforce_gaps = []
    for s in all_sites:
        if s.status == "Active" and s.required_workers > 0:
            gap = s.required_workers - s.assigned_workers
            if gap > 0:
                workforce_gaps.append({
                    "site_id": s.uid,
                    "site_name": s.name,
                    "project_name": s.project_name,
                    "required_workers": s.required_workers,
                    "assigned_workers": s.assigned_workers,
                    "gap": gap,
                    "fill_percentage": round(
                        (s.assigned_workers / s.required_workers) * 100, 1
                    ) if s.required_workers else 0,
                })
    workforce_gaps.sort(key=lambda x: x["gap"], reverse=True)

    # --- Projects list (active only) ---
    projects_data = []
    for p in all_projects:
        if p.status == "Active":
            # Find latest contract expiry for this project
            project_contracts = [c for c in all_contracts if c.project_id == p.uid]
            nearest_expiry = None
            days_to_expiry = None
            if project_contracts:
                nearest = min(project_contracts, key=lambda c: c.end_date)
                nearest_expiry = nearest.end_date.isoformat()
                days_to_expiry = (nearest.end_date - today).days

            projects_data.append({
                "project_id": p.uid,
                "project_code": p.project_code,
                "project_name": p.project_name,
                "client_name": p.client_name,
                "status": p.status,
                "total_sites": p.total_sites,
                "total_assigned_employees": p.total_assigned_employees,
                "nearest_contract_expiry": nearest_expiry,
                "days_to_expiry": days_to_expiry,
                "contract_alert": days_to_expiry is not None and days_to_expiry <= 30,
            })

    workforce_utilization = round(
        (assigned_employees / total_employees * 100) if total_employees > 0 else 0, 1
    )

    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "on_hold_projects": on_hold_projects,
        "total_sites": total_sites,
        "total_employees": total_employees,
        "available_employees": available_employees,
        "assigned_employees": assigned_employees,
        "active_external_workers": active_external,
        "contracts_expiring_soon": len(expiring_soon),
        "workforce_utilization": workforce_utilization,
        "projects": projects_data,
        "expiring_contracts": expiring_soon,
        "workforce_gaps": workforce_gaps,
    }


@router.get("/workflow-summary", dependencies=[Depends(get_current_active_user)])
async def get_workflow_summary():
    """
    Returns aggregate statistics for the Workflow Overview dashboard.
    Includes Projects → Contracts → Sites hierarchy data with workforce stats.
    """
    today = datetime.now()

    all_projects= await Project.find().sort("+uid").to_list()
    all_contracts = await Contract.find().sort("+uid").to_list()
    all_sites = await Site.find().sort("+uid").to_list()

    active_temp = await TemporaryAssignment.find(
        TemporaryAssignment.status == "Active"
    ).to_list()

    total_temp_cost = sum(
        (ta.daily_rate or 0.0) * (ta.total_days or 0) if ta.rate_type == "Daily"
        else (ta.hourly_rate or 0.0) * 8 * (ta.total_days or 0)
        for ta in active_temp
    )

    # Contract expiry alerts
    expiring_soon = []
    for c in all_contracts:
        if c.status == "Active" and c.end_date:
            days_left = (c.end_date - today).days
            if days_left <= 30:
                expiring_soon.append({
                    "contract_id": c.uid,
                    "contract_code": c.contract_code,
                    "contract_name": c.contract_name,
                    "project_name": c.project_name,
                    "end_date": c.end_date.isoformat(),
                    "days_remaining": days_left,
                    "alert_level": "danger" if days_left <= 7 else "warning",
                })
    expiring_soon.sort(key=lambda x: x["days_remaining"])

    # Sites with workforce gaps
    workforce_gaps = [
        {
            "site_id": s.uid,
            "site_code": s.site_code,
            "site_name": s.name,
            "project_name": s.project_name,
            "required_workers": s.required_workers,
            "assigned_workers": s.assigned_workers,
            "gap": s.required_workers - s.assigned_workers,
        }
        for s in all_sites
        if s.status == "Active" and s.required_workers > 0 and s.assigned_workers < s.required_workers
    ]

    # Build hierarchy: project → contracts → sites
    contracts_by_project: dict = {}
    for c in all_contracts:
        pid = c.project_id
        if pid not in contracts_by_project:
            contracts_by_project[pid] = []
        contracts_by_project[pid].append(c)

    sites_by_contract: dict = {}
    for s in all_sites:
        cid = s.contract_id
        if cid not in sites_by_contract:
            sites_by_contract[cid] = []
        sites_by_contract[cid].append(s)

    hierarchy = []
    for p in all_projects:
        p_contracts = contracts_by_project.get(p.uid, [])
        p_contracts_data = []
        for c in p_contracts:
            c_sites = sites_by_contract.get(c.uid, [])
            p_contracts_data.append({
                "uid": c.uid,
                "contract_code": c.contract_code,
                "contract_name": c.contract_name,
                "status": c.status,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "days_remaining": c.days_remaining,
                "contract_value": c.contract_value,
                "sites": [
                    {
                        "uid": s.uid,
                        "site_code": s.site_code,
                        "name": s.name,
                        "location": s.location,
                        "status": s.status,
                        "assigned_workers": s.assigned_workers,
                        "required_workers": s.required_workers,
                        "assigned_manager_name": s.assigned_manager_name,
                    }
                    for s in c_sites
                ],
            })
        hierarchy.append({
            "uid": p.uid,
            "project_code": p.project_code,
            "project_name": p.project_name,
            "client_name": p.client_name,
            "status": p.status,
            "contracts": p_contracts_data,
        })

    total_contract_value = sum(c.contract_value or 0 for c in all_contracts if c.status == "Active")

    return {
        "total_projects": len(all_projects),
        "active_projects": sum(1 for p in all_projects if p.status == "Active"),
        "completed_projects": sum(1 for p in all_projects if p.status == "Completed"),
        "total_contracts": len(all_contracts),
        "active_contracts": sum(1 for c in all_contracts if c.status == "Active"),
        "expiring_contracts": len(expiring_soon),
        "total_sites": len(all_sites),
        "active_sites": sum(1 for s in all_sites if s.status == "Active"),
        "total_active_temp_workers": len(active_temp),
        "monthly_temp_cost": total_temp_cost,
        "total_contract_value": total_contract_value,
        "expiring_soon": expiring_soon,
        "workforce_gaps": workforce_gaps,
        "hierarchy": hierarchy,
    }


@router.get("/profit-loss", dependencies=[Depends(require_permission("finance:view"))])
async def get_profit_loss_summary():
    """
    Returns comprehensive profit & loss analytics:
    - Total revenue, costs, profit
    - Per-contract profitability
    - Monthly trends (last 6 months estimate)
    - Cost breakdown (employee vs external)
    - At-risk contracts
    """
    # Business rule thresholds
    AT_RISK_MARGIN_THRESHOLD = 10.0   # Below 10% margin = at-risk
    DAYS_PER_MONTH = 30.44            # Average days per month for duration calculation

    contracts = await Contract.find(Contract.status == "Active").to_list()

    contract_analytics = []
    total_revenue = 0.0
    total_costs = 0.0

    for contract in contracts:
        # Revenue
        revenue = contract.contract_value or 0.0
        total_revenue += revenue

        # Calculate duration in months using average days per month
        if contract.start_date and contract.end_date:
            duration_days = (contract.end_date - contract.start_date).days
            duration_months = max(1.0, duration_days / DAYS_PER_MONTH)
        else:
            duration_months = 1.0

        # Get all sites for this contract
        sites = await Site.find(Site.contract_id == contract.uid).to_list()
        site_ids = [s.uid for s in sites]

        # Calculate employee costs via EmployeeAssignment
        employee_cost_monthly = 0.0
        employee_count = 0

        for site in sites:
            assignments = await EmployeeAssignment.find(
                EmployeeAssignment.site_id == site.uid,
                EmployeeAssignment.status == "Active"
            ).to_list()

            for assignment in assignments:
                employee = await Employee.find_one(Employee.uid == assignment.employee_id)
                if employee:
                    employee_cost_monthly += employee.basic_salary or 0.0
                    employee_count += 1

        total_employee_cost = employee_cost_monthly * duration_months

        # Get external worker costs via TemporaryAssignment for these sites
        if site_ids:
            temp_workers = await TemporaryAssignment.find(
                {"site_id": {"$in": site_ids}, "status": "Active"}
            ).to_list()
        else:
            temp_workers = []

        external_cost = sum(
            (tw.daily_rate or 0.0) * (tw.total_days or 1)
            for tw in temp_workers
        )

        # Total costs and profit
        costs = total_employee_cost + external_cost
        total_costs += costs

        profit = revenue - costs
        margin = (profit / revenue * 100.0) if revenue > 0 else 0.0

        # Status determination based on profit margin
        if margin < 0:
            status = "loss"
            status_color = "red"
        elif margin < AT_RISK_MARGIN_THRESHOLD:
            status = "at-risk"
            status_color = "orange"
        else:
            status = "profitable"
            status_color = "green"

        contract_analytics.append({
            "contract_id": contract.uid,
            "contract_code": contract.contract_code,
            "contract_name": contract.contract_name or contract.contract_code,
            "project_name": contract.project_name or "",
            "revenue": round(revenue, 2),
            "employee_costs": round(total_employee_cost, 2),
            "external_costs": round(external_cost, 2),
            "total_costs": round(costs, 2),
            "profit": round(profit, 2),
            "margin": round(margin, 1),
            "status": status,
            "status_color": status_color,
            "employee_count": employee_count,
            "duration_months": round(duration_months, 1),
        })

    # Sort by profit descending
    contract_analytics.sort(key=lambda x: x["profit"], reverse=True)

    # Overall metrics
    net_profit = total_revenue - total_costs
    overall_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # Cost breakdown
    total_employee_costs = sum(c["employee_costs"] for c in contract_analytics)
    total_external_costs = sum(c["external_costs"] for c in contract_analytics)

    cost_breakdown = {
        "employee_salaries": round(total_employee_costs, 2),
        "external_workers": round(total_external_costs, 2),
        "employee_percentage": round(
            (total_employee_costs / total_costs * 100.0) if total_costs > 0 else 0.0, 1
        ),
        "external_percentage": round(
            (total_external_costs / total_costs * 100.0) if total_costs > 0 else 0.0, 1
        ),
    }

    # Monthly trend (last 6 months) – distributes totals evenly as a baseline estimate
    monthly_trend = []
    today = datetime.now()
    for i in range(6, 0, -1):
        # Calculate the first day of each of the past 6 months
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_name = datetime(year, month, 1).strftime("%b")
        monthly_trend.append({
            "month": month_name,
            "revenue": round(total_revenue / 6.0, 2),
            "costs": round(total_costs / 6.0, 2),
            "profit": round(net_profit / 6.0, 2),
        })

    # At-risk contracts
    at_risk = [c for c in contract_analytics if c["status"] in ["loss", "at-risk"]]

    return {
        "total_revenue": round(total_revenue, 2),
        "total_costs": round(total_costs, 2),
        "net_profit": round(net_profit, 2),
        "profit_margin": round(overall_margin, 1),
        "active_contracts": len(contracts),
        "profitable_contracts": sum(1 for c in contract_analytics if c["status"] == "profitable"),
        "at_risk_contracts": len(at_risk),
        "contracts": contract_analytics,
        "cost_breakdown": cost_breakdown,
        "monthly_trend": monthly_trend,
        "at_risk": at_risk,
    }