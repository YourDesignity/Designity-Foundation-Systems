"""Service layer for permanent employee assignments."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class AssignmentService(BaseService):
    """Employee assignment CRUD and query operations."""

    async def create_assignment(self, payload: Any):
        from backend.models import EmployeeAssignment

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("employee_assignments")
        assignment = EmployeeAssignment(**data)
        await assignment.insert()
        return assignment

    async def get_assignment_by_id(self, assignment_id: int):
        from backend.models import EmployeeAssignment

        assignment = await EmployeeAssignment.find_one(EmployeeAssignment.uid == assignment_id)
        if not assignment:
            self.raise_not_found(f"Assignment {assignment_id} not found")
        return assignment

    async def get_assignments(self):
        from backend.models import EmployeeAssignment

        return await EmployeeAssignment.find_all().sort("+uid").to_list()

    async def update_assignment(self, assignment_id: int, payload: Any):
        assignment = await self.get_assignment_by_id(assignment_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(assignment, field, value)
        await assignment.save()
        return assignment

    async def delete_assignment(self, assignment_id: int) -> bool:
        assignment = await self.get_assignment_by_id(assignment_id)
        await assignment.delete()
        return True
