"""Service layer for project operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class ProjectService(BaseService):
    """Project CRUD and lifecycle operations."""

    async def create_project(self, payload: Any):
        from backend.models import Project

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("projects")
        project = Project(**data)
        await project.insert()
        return project

    async def get_project_by_id(self, project_id: int):
        from backend.models import Project

        project = await Project.find_one(Project.uid == project_id)
        if not project:
            self.raise_not_found(f"Project {project_id} not found")
        return project

    async def get_projects(self):
        from backend.models import Project

        return await Project.find_all().sort("+uid").to_list()

    async def update_project(self, project_id: int, payload: Any):
        project = await self.get_project_by_id(project_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        for field, value in data.items():
            setattr(project, field, value)
        await project.save()
        return project

    async def delete_project(self, project_id: int) -> bool:
        project = await self.get_project_by_id(project_id)
        await project.delete()
        return True
