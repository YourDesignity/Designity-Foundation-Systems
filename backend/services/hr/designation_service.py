"""Service layer for designation management."""

import logging
from typing import Any

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class DesignationService(BaseService):
    """Business logic for designation CRUD and reporting."""

    async def create_designation(self, payload: Any):
        """
        Create a designation.

        Validations:
        - Title must be unique

        Args:
            payload: Designation payload (dict or model)

        Returns:
            Created designation document
        """
        from backend.models import Designation

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        title = data.get("title")
        if not title:
            self.raise_bad_request("Designation title is required")

        existing = await Designation.find_one(Designation.title == title)
        if existing:
            self.raise_bad_request("Designation already exists")

        designation = Designation(uid=await self.get_next_uid("designations"), title=title)
        await designation.insert()
        logger.info("Designation created: %s", title)
        return designation

    async def get_designation_hierarchy(self) -> list[dict]:
        """
        Get designation list with employee counts.

        Returns:
            Sorted hierarchy-like view for UI usage
        """
        from backend.models import Designation

        designations = await Designation.find_all().sort("+title").to_list()
        result = []
        for item in designations:
            count = await self.get_employee_count_by_designation(item.title)
            result.append({"designation_id": item.uid, "title": item.title, "employee_count": count})
        return result

    async def get_employee_count_by_designation(self, designation_title: str) -> int:
        """
        Count active employees for designation.

        Args:
            designation_title: Designation title

        Returns:
            Employee count
        """
        from backend.models import Employee

        return await Employee.find(Employee.designation == designation_title, Employee.status == "Active").count()

    async def get_designation_by_id(self, designation_id: int):
        from backend.models import Designation

        designation = await Designation.find_one(Designation.uid == designation_id)
        if not designation:
            self.raise_not_found(f"Designation {designation_id} not found")
        return designation

    async def get_designations(self):
        from backend.models import Designation

        return await Designation.find_all().sort("+uid").to_list()

    async def update_designation(self, designation_id: int, payload: Any):
        designation = await self.get_designation_by_id(designation_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(designation, field, value)
        await designation.save()
        return designation

    async def delete_designation(self, designation_id: int) -> bool:
        designation = await self.get_designation_by_id(designation_id)
        await designation.delete()
        logger.info("Designation deleted: ID %s", designation_id)
        return True
