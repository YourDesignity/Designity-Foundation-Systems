"""Service layer for manager profile and assignment operations."""

import logging
from datetime import datetime
from typing import Any, Iterable, List

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class ManagerService(BaseService):
    """Business logic for site manager profiles and managed sites."""

    async def create_manager_profile(self, payload: Any, created_by_admin_id: int | None = None):
        """
        Create a manager (Admin + ManagerProfile).

        Validations:
        - Email must be unique
        - Required manager profile fields must be provided

        Args:
            payload: Create manager payload (pydantic model or dict)
            created_by_admin_id: Admin UID performing the action

        Returns:
            Created admin/profile IDs

        Raises:
            HTTPException 400: Validation failure
        """
        from backend.models import Admin, ManagerProfile
        from backend.security import get_password_hash

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        email = data.get("email")
        if not email:
            self.raise_bad_request("Email is required")

        existing_admin = await Admin.find_one(Admin.email == email)
        if existing_admin:
            self.raise_bad_request("Email already exists")

        if not data.get("password"):
            self.raise_bad_request("Password is required")

        assigned_sites = data.get("assigned_site_uids") or data.get("site_uids") or []
        admin_uid = await self.get_next_uid("admins")
        admin = Admin(
            uid=admin_uid,
            email=email,
            hashed_password=get_password_hash(data["password"]),
            full_name=data.get("full_name", ""),
            designation=data.get("designation", ""),
            role="Site Manager",
            permissions=data.get(
                "permissions",
                [
                    "employee:view_assigned",
                    "attendance:update",
                    "site:view",
                    "schedule:edit",
                    "schedule:view_assigned",
                ],
            ),
            assigned_site_uids=assigned_sites,
            is_active=True,
            has_manager_profile=True,
        )
        await admin.insert()

        profile_uid = await self.get_next_uid("manager_profiles")
        date_of_joining = data.get("date_of_joining")
        if isinstance(date_of_joining, str):
            date_of_joining = datetime.fromisoformat(date_of_joining)

        profile = ManagerProfile(
            uid=profile_uid,
            admin_id=admin.uid,
            full_name=data.get("full_name", ""),
            designation=data.get("designation", ""),
            monthly_salary=float(data.get("monthly_salary", 0.0)),
            allowances=float(data.get("allowances") or 0.0),
            date_of_joining=date_of_joining or datetime.now(),
            phone=data.get("phone"),
            address=data.get("address"),
            emergency_contact=data.get("emergency_contact"),
            emergency_phone=data.get("emergency_phone"),
            bank_name=data.get("bank_name"),
            account_number=data.get("account_number"),
            iban=data.get("iban"),
            nationality=data.get("nationality"),
            passport_number=data.get("passport_number"),
            civil_id=data.get("civil_id"),
            created_by_admin_id=created_by_admin_id or data.get("created_by_admin_id") or 0,
        )
        await profile.insert()

        logger.info("Manager created: %s (admin=%s profile=%s)", admin.email, admin.uid, profile.uid)
        return {"admin_id": admin.uid, "profile_id": profile.uid}

    async def assign_sites_to_manager(self, manager_id: int, site_uids: Iterable[int]) -> dict:
        """
        Assign sites to a manager account.

        Validations:
        - Manager must exist and have Site Manager role
        - All site IDs must exist

        Args:
            manager_id: Manager admin UID
            site_uids: Site UID list

        Returns:
            Assignment summary

        Raises:
            HTTPException 404: Manager or site not found
            HTTPException 400: Invalid manager role
        """
        from backend.models import Admin, Site

        manager = await Admin.find_one(Admin.uid == manager_id)
        if not manager:
            self.raise_not_found("Manager not found")
        if manager.role != "Site Manager":
            self.raise_bad_request("Admin is not a Site Manager")

        site_list = sorted({int(site_id) for site_id in site_uids})
        if site_list:
            existing_sites = await Site.find(Site.uid.in_(site_list)).to_list()
            if len(existing_sites) != len(site_list):
                existing_ids = {s.uid for s in existing_sites}
                missing = sorted(set(site_list) - existing_ids)
                self.raise_not_found(f"Site(s) not found: {missing}")

        manager.assigned_site_uids = site_list
        await manager.save()

        logger.info("Manager %s assigned sites: %s", manager_id, site_list)
        return {"manager_id": manager_id, "assigned_site_uids": site_list}

    async def get_manager_sites(self, manager_id: int) -> dict:
        """
        Get managed sites with staffing summaries.

        Validations:
        - Manager must exist

        Args:
            manager_id: Manager admin UID

        Returns:
            Site summary payload

        Raises:
            HTTPException 404: Manager not found
        """
        from backend.models import Admin, EmployeeAssignment, Site

        manager = await Admin.find_one(Admin.uid == manager_id)
        if not manager:
            self.raise_not_found("Manager not found")

        sites: List[Any] = await Site.find(Site.assigned_manager_id == manager_id).to_list()
        site_summaries: list[dict] = []
        for site in sites:
            assignments = await EmployeeAssignment.find(
                EmployeeAssignment.site_id == site.uid,
                EmployeeAssignment.status == "Active",
            ).count()
            site_dict = site.model_dump(mode="json")
            site_dict["active_employees"] = assignments
            site_dict["is_understaffed"] = site.is_understaffed
            site_dict["headcount_shortage"] = site.headcount_shortage
            site_summaries.append(site_dict)

        return {
            "manager_id": manager_id,
            "manager_name": manager.full_name,
            "total_sites": len(site_summaries),
            "sites": site_summaries,
        }
