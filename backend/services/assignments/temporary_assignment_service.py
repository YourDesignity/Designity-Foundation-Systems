"""Service layer for temporary assignment operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class TemporaryAssignmentService(BaseService):
    """Temporary assignment CRUD and status operations."""

    async def create_temporary_assignment(self, payload: Any):
        from backend.models import TemporaryAssignment

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("temporary_assignments")
        assignment = TemporaryAssignment(**data)
        await assignment.insert()
        return assignment

    async def get_temporary_assignment_by_id(self, assignment_id: int):
        from backend.models import TemporaryAssignment

        assignment = await TemporaryAssignment.find_one(TemporaryAssignment.uid == assignment_id)
        if not assignment:
            self.raise_not_found(f"Temporary assignment {assignment_id} not found")
        return assignment

    async def get_temporary_assignments(self):
        from backend.models import TemporaryAssignment

        return await TemporaryAssignment.find_all().sort("+uid").to_list()

    async def update_temporary_assignment(self, assignment_id: int, payload: Any):
        assignment = await self.get_temporary_assignment_by_id(assignment_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(assignment, field, value)
        await assignment.save()
        return assignment

    async def delete_temporary_assignment(self, assignment_id: int) -> bool:
        assignment = await self.get_temporary_assignment_by_id(assignment_id)
        await assignment.delete()
        return True
