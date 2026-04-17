"""Service layer for project-level analytics: contract values, workforce stats, and external worker costs."""

from datetime import datetime

from backend.services.base_service import BaseService


class ProjectAnalyticsService(BaseService):
    """Aggregates project performance, workforce, and external-worker analytics."""

    async def get_project_analytics(self) -> dict:
        """Return per-project performance metrics including contract value, workforce, and site progress."""
        from backend.models import (
            Contract,
            EmployeeAssignment,
            Project,
            Site,
            TemporaryAssignment,
        )

        today = datetime.now()
        projects = await Project.find().to_list()
        contracts = await Contract.find().to_list()

        contracts_by_project: dict = {}
        for c in contracts:
            contracts_by_project.setdefault(c.project_id, []).append(c)

        result = []
        total_contract_value = 0.0
        active_contract_value = 0.0

        for p in projects:
            p_contracts = contracts_by_project.get(p.uid, [])
            contract_value = sum(c.contract_value for c in p_contracts)
            total_contract_value += contract_value
            if p.status == "Active":
                active_contract_value += contract_value

            sites = await Site.find(Site.project_id == p.uid).to_list()
            completed_sites = sum(1 for s in sites if s.status == "Completed")
            active_sites = sum(1 for s in sites if s.status == "Active")
            total_sites = len(sites)
            completion_pct = round(
                (completed_sites / total_sites * 100) if total_sites else 0, 1
            )

            perm_count = await EmployeeAssignment.find(
                EmployeeAssignment.project_id == p.uid,
                EmployeeAssignment.status == "Active",
            ).count()

            temp_assignments = await TemporaryAssignment.find(
                TemporaryAssignment.project_id == p.uid,
            ).to_list()
            active_temp = [t for t in temp_assignments if t.status == "Active"]
            external_cost = sum(
                (t.daily_rate * t.total_days if t.rate_type == "Daily" else t.hourly_rate * t.total_days * 8)
                for t in temp_assignments
            )

            nearest_expiry = None
            days_to_expiry = None
            active_contracts = [c for c in p_contracts if c.status == "Active"]
            if active_contracts:
                nearest = min(active_contracts, key=lambda c: c.end_date)
                nearest_expiry = nearest.end_date.isoformat()
                days_to_expiry = (nearest.end_date - today).days

            result.append({
                "project_id": p.uid,
                "project_code": p.project_code,
                "project_name": p.project_name,
                "client_name": p.client_name,
                "status": p.status,
                "contract_value": contract_value,
                "external_labor_cost": round(external_cost, 2),
                "total_sites": total_sites,
                "active_sites": active_sites,
                "completed_sites": completed_sites,
                "completion_percentage": completion_pct,
                "permanent_workers": perm_count,
                "active_external_workers": len(active_temp),
                "nearest_contract_expiry": nearest_expiry,
                "days_to_expiry": days_to_expiry,
            })

        result.sort(key=lambda x: x["contract_value"], reverse=True)

        return {
            "projects": result,
            "summary": {
                "total_projects": len(projects),
                "total_contract_value": round(total_contract_value, 2),
                "active_contract_value": round(active_contract_value, 2),
            },
        }

    async def get_workforce_analytics(self) -> dict:
        """Return workforce utilization analytics: top assigned employees, utilization rates, avg duration."""
        from backend.models import Employee, EmployeeAssignment

        all_assignments = await EmployeeAssignment.find().to_list()

        emp_stats: dict = {}
        for a in all_assignments:
            eid = a.employee_id
            if eid not in emp_stats:
                emp_stats[eid] = {
                    "employee_id": eid,
                    "employee_name": a.employee_name,
                    "designation": a.employee_designation,
                    "total_assignments": 0,
                    "active_assignments": 0,
                    "total_days": 0,
                }
            emp_stats[eid]["total_assignments"] += 1
            if a.status == "Active":
                emp_stats[eid]["active_assignments"] += 1
            if a.assignment_start and a.assignment_end:
                days = (a.assignment_end - a.assignment_start).days
                emp_stats[eid]["total_days"] += max(days, 0)

        top_employees = sorted(
            emp_stats.values(),
            key=lambda x: x["total_assignments"],
            reverse=True,
        )[:10]

        completed = [
            a for a in all_assignments
            if a.status == "Completed" and a.assignment_start and a.assignment_end
        ]
        avg_duration = 0
        if completed:
            total_days = sum(
                max((a.assignment_end - a.assignment_start).days, 0) for a in completed
            )
            avg_duration = round(total_days / len(completed), 1)

        total_company = await Employee.find(
            Employee.status == "Active",
            Employee.employee_type == "Company",
        ).count()
        assigned_company = await Employee.find(
            Employee.status == "Active",
            Employee.employee_type == "Company",
            Employee.is_currently_assigned == True,
        ).count()

        return {
            "top_employees": top_employees,
            "average_assignment_duration_days": avg_duration,
            "total_company_employees": total_company,
            "assigned_company_employees": assigned_company,
            "utilization_rate": round(
                (assigned_company / total_company * 100) if total_company else 0, 1
            ),
        }

    async def get_external_worker_analytics(self) -> dict:
        """Return external worker usage statistics and cost breakdown per project."""
        from backend.models import Project, TemporaryAssignment

        all_temp = await TemporaryAssignment.find().to_list()

        total_cost = sum(
            (t.daily_rate * t.total_days if t.rate_type == "Daily" else t.hourly_rate * t.total_days * 8)
            for t in all_temp
        )

        project_costs: dict = {}
        for t in all_temp:
            pid = t.project_id
            if pid not in project_costs:
                project_costs[pid] = {
                    "project_id": pid,
                    "total_days": 0,
                    "total_cost": 0.0,
                    "worker_count": 0,
                }
            cost = (
                t.daily_rate * t.total_days
                if t.rate_type == "Daily"
                else t.hourly_rate * t.total_days * 8
            )
            project_costs[pid]["total_days"] += t.total_days
            project_costs[pid]["total_cost"] += cost
            project_costs[pid]["worker_count"] += 1

        projects = await Project.find().to_list()
        project_map = {p.uid: p for p in projects}
        per_project = []
        for pid, data in project_costs.items():
            proj = project_map.get(pid)
            per_project.append({
                **data,
                "project_code": proj.project_code if proj else f"PRJ-{pid}",
                "project_name": proj.project_name if proj else "Unknown",
                "total_cost": round(data["total_cost"], 2),
            })
        per_project.sort(key=lambda x: x["total_cost"], reverse=True)

        active_count = sum(1 for t in all_temp if t.status == "Active")

        return {
            "total_external_assignments": len(all_temp),
            "active_external_workers": active_count,
            "total_external_cost": round(total_cost, 2),
            "per_project": per_project,
        }
