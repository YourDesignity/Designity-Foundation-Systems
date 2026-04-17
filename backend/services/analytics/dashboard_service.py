"""Service layer for dashboard metric aggregation."""

import logging
from datetime import date, datetime, timedelta

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class DashboardService(BaseService):
    """Dashboard metrics across HR, project, and finance domains."""

    # ====================================================================
    # DASHBOARD SUMMARY
    # ====================================================================

    async def get_dashboard_summary(self) -> dict:
        """
        Get high-level dashboard metrics.

        Returns:
            Summary metrics for employees, projects, contracts, and revenue
        """
        from backend.models import Contract, Employee, Project, Site
        from backend.services.finance.invoice_service import InvoiceService

        today = date.today()
        total_revenue = await InvoiceService().calculate_total_revenue(today.month, today.year)

        return {
            "employees": await Employee.find(Employee.status == "Active").count(),
            "projects": await Project.find_all().count(),
            "active_projects": await Project.find(Project.status == "Active").count(),
            "sites": await Site.find_all().count(),
            "contracts": await Contract.find_all().count(),
            "monthly_revenue": float(total_revenue),
        }

    async def get_hr_metrics(self) -> dict:
        """Get HR metrics including attendance and hiring activity."""
        from backend.models import Attendance, Employee

        today = date.today()
        month_start = date(today.year, today.month, 1)

        attendance_rows = await Attendance.find_all().to_list()
        monthly_rows = [row for row in attendance_rows if self._date_string_in_range(row.date, month_start, today)]
        present_rows = [row for row in monthly_rows if (row.status or "").lower() == "present"]

        employees = await Employee.find_all().to_list()
        new_hires = [
            emp
            for emp in employees
            if emp.date_of_joining and emp.date_of_joining.year == today.year and emp.date_of_joining.month == today.month
        ]

        return {
            "active_employees": len([emp for emp in employees if emp.status == "Active"]),
            "new_hires": len(new_hires),
            "attendance_records": len(monthly_rows),
            "attendance_rate": round((len(present_rows) / len(monthly_rows) * 100.0), 2) if monthly_rows else 0.0,
        }

    async def get_project_metrics(self) -> dict:
        """Get project metrics by status and contract type."""
        from backend.models import Contract, Project

        projects = await Project.find_all().to_list()
        contracts = await Contract.find_all().to_list()

        by_status: dict[str, int] = {}
        for project in projects:
            status = project.status or "Unknown"
            by_status[status] = by_status.get(status, 0) + 1

        by_contract_type: dict[str, int] = {}
        for contract in contracts:
            ctype = contract.contract_type or "Unknown"
            by_contract_type[ctype] = by_contract_type.get(ctype, 0) + 1

        return {
            "total_projects": len(projects),
            "projects_by_status": by_status,
            "total_contracts": len(contracts),
            "contracts_by_type": by_contract_type,
        }

    async def get_financial_metrics(self) -> dict:
        """Get finance metrics for dashboard cards."""
        from backend.services.finance.invoice_service import InvoiceService

        invoice_service = InvoiceService()
        today = date.today()

        monthly_revenue = await invoice_service.calculate_total_revenue(today.month, today.year)
        unpaid_invoices = await invoice_service.get_unpaid_invoices()
        overdue_invoices = await invoice_service.get_overdue_invoices()

        return {
            "monthly_revenue": float(monthly_revenue),
            "unpaid_invoices": len(unpaid_invoices),
            "overdue_invoices": len(overdue_invoices),
            "outstanding_amount": await invoice_service.calculate_outstanding_amount(),
        }

    async def get_dashboard_alerts(self) -> dict:
        """Get operational alerts (unfilled slots, overdue invoices, low stock at/below threshold)."""
        from backend.models import Material
        from backend.services.finance.invoice_service import InvoiceService
        from backend.services.role_contracts_service import RoleContractsService

        overdue_invoices = await InvoiceService().get_overdue_invoices()
        unfilled_slots = await RoleContractsService().get_unfilled_slots()
        materials = await Material.find_all().to_list()
        # Treat stock at or below minimum_stock as alert-worthy.
        low_stock = [row for row in materials if row.current_stock <= row.minimum_stock]

        return {
            "unfilled_slots": len(unfilled_slots),
            "overdue_invoices": len(overdue_invoices),
            "low_stock_items": len(low_stock),
            "low_stock_materials": [
                {
                    "material_id": row.uid,
                    "material_code": row.material_code,
                    "name": row.name,
                    "current_stock": row.current_stock,
                    "minimum_stock": row.minimum_stock,
                }
                for row in low_stock
            ],
        }

    async def get_attendance_trend(self, days: int = 30) -> list[dict]:
        """Get attendance trend for the last N days."""
        if days <= 0:
            self.raise_bad_request("days must be greater than zero")

        from backend.models import Attendance

        records = await Attendance.find_all().to_list()
        today = date.today()
        start = today - timedelta(days=days - 1)

        trend: list[dict] = []
        for idx in range(days):
            point = start + timedelta(days=idx)
            day_rows = [row for row in records if self._date_string_matches(row.date, point)]
            present_count = len([row for row in day_rows if (row.status or "").lower() == "present"])
            trend.append(
                {
                    "date": point.isoformat(),
                    "records": len(day_rows),
                    "present": present_count,
                    "attendance_rate": round((present_count / len(day_rows) * 100.0), 2) if day_rows else 0.0,
                }
            )

        return trend

    async def get_revenue_trend(self, months: int = 6) -> list[dict]:
        """Get revenue trend for the last N months."""
        if months <= 0:
            self.raise_bad_request("months must be greater than zero")

        from backend.services.finance.invoice_service import InvoiceService

        invoice_service = InvoiceService()
        today = date.today()
        trend: list[dict] = []

        for offset in range(months - 1, -1, -1):
            month = today.month - offset
            year = today.year
            while month <= 0:
                month += 12
                year -= 1

            amount = await invoice_service.calculate_total_revenue(month, year)
            trend.append({"month": f"{year:04d}-{month:02d}", "revenue": float(amount)})

        return trend

    # ====================================================================
    # INTERNAL HELPERS
    # ====================================================================

    @staticmethod
    def _date_string_matches(value: str | None, target: date) -> bool:
        if not value:
            return False
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return False
        return parsed == target

    @staticmethod
    def _date_string_in_range(value: str | None, start: date, end: date) -> bool:
        if not value:
            return False
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return False
        return start <= parsed <= end

    # ====================================================================
    # BACKWARD-COMPAT HELPER
    # ====================================================================

    async def get_overview_metrics(self) -> dict:
        """Backward-compatible wrapper for legacy callers."""
        return await self.get_dashboard_summary()

    # ====================================================================
    # SYSTEM / UI ENDPOINTS
    # ====================================================================

    async def get_system_stats(self) -> dict:
        """Return counts of all major collections for UI cards."""
        from backend.models import Admin, Attendance, Employee, Schedule, Site

        return {
            "employees": await Employee.count(),
            "admins": await Admin.count(),
            "sites": await Site.count(),
            "attendance_records": await Attendance.count(),
            "schedules": await Schedule.count(),
        }

    async def get_system_health(self) -> dict:
        """Return server RAM/CPU usage."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        return {
            "cpu_usage": psutil.cpu_percent(),
            "ram_usage_mb": process.memory_info().rss / 1024 / 1024,
            "total_ram_percent": psutil.virtual_memory().percent,
        }

    async def get_schema_visualization(self) -> dict:
        """Return nodes and edges for the database-relationship graph."""
        nodes = [
            {"id": 1, "label": "Employees", "color": "#4CAF50"},
            {"id": 2, "label": "Sites", "color": "#2196F3"},
            {"id": 3, "label": "Admins\n(Managers)", "color": "#FF9800"},
            {"id": 4, "label": "Attendance", "color": "#9C27B0"},
            {"id": 5, "label": "Schedules", "color": "#607D8B"},
        ]
        edges = [
            {"from": 3, "to": 2, "label": "manages", "arrows": "to"},
            {"from": 3, "to": 1, "label": "manages", "arrows": "to"},
            {"from": 1, "to": 4, "label": "logs", "arrows": "to"},
            {"from": 2, "to": 4, "label": "location", "arrows": "to"},
            {"from": 1, "to": 5, "label": "assigned", "arrows": "to"},
            {"from": 2, "to": 5, "label": "location", "arrows": "to"},
        ]
        return {"nodes": nodes, "edges": edges}

    async def get_live_logs(self) -> list:
        """Read the last 50 lines of the main application log."""
        import os

        log_file = "logs/app_main.log"
        if not os.path.exists(log_file):
            return ["Log file not created yet."]
        with open(log_file, "r") as f:
            lines = f.readlines()
            return lines[-50:]

    # ====================================================================
    # COMPREHENSIVE SUMMARY
    # ====================================================================

    async def get_comprehensive_summary(self) -> dict:
        """Return a comprehensive dashboard summary for the overview page."""
        from backend.models import Contract, Employee, Project, Site, TemporaryAssignment
        from datetime import datetime

        today = datetime.now()
        total_employees = await Employee.find(Employee.status == "Active").count()
        available_employees = await Employee.find(
            Employee.status == "Active",
            Employee.is_currently_assigned == False  # noqa: E712
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

        projects_data = []
        for p in all_projects:
            if p.status == "Active":
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

    # ====================================================================
    # WORKFLOW SUMMARY
    # ====================================================================

    async def get_workflow_summary(self) -> dict:
        """Return aggregate statistics for the Workflow Overview dashboard."""
        from backend.models import Contract, Project, Site, TemporaryAssignment
        from datetime import datetime

        today = datetime.now()

        all_projects = await Project.find().sort("+uid").to_list()
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

    # ====================================================================
    # PROFIT & LOSS
    # ====================================================================

    async def get_profit_loss_summary(self) -> dict:
        """Return comprehensive profit & loss analytics per contract."""
        from backend.models import Contract, Employee, EmployeeAssignment, Site, TemporaryAssignment
        from datetime import datetime

        AT_RISK_MARGIN_THRESHOLD = 10.0
        DAYS_PER_MONTH = 30.44

        contracts = await Contract.find(Contract.status == "Active").to_list()

        contract_analytics = []
        total_revenue = 0.0
        total_costs = 0.0

        for contract in contracts:
            revenue = contract.contract_value or 0.0
            total_revenue += revenue

            if contract.start_date and contract.end_date:
                duration_days = (contract.end_date - contract.start_date).days
                duration_months = max(1.0, duration_days / DAYS_PER_MONTH)
            else:
                duration_months = 1.0

            sites = await Site.find(Site.contract_id == contract.uid).to_list()
            site_ids = [s.uid for s in sites]

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

            costs = total_employee_cost + external_cost
            total_costs += costs

            profit = revenue - costs
            margin = (profit / revenue * 100.0) if revenue > 0 else 0.0

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

        contract_analytics.sort(key=lambda x: x["profit"], reverse=True)

        net_profit = total_revenue - total_costs
        overall_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

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

        monthly_trend = []
        today = datetime.now()
        for i in range(6, 0, -1):
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
