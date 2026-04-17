# backend/routers/project_analytics.py

from fastapi import APIRouter, Depends
from backend.security import get_current_active_user

router = APIRouter(
    prefix="/analytics",
    tags=["Project Analytics"],
    dependencies=[Depends(get_current_active_user)],
)


def _get_service():
    from backend.services.project_analytics_service import ProjectAnalyticsService
    return ProjectAnalyticsService()


@router.get("/projects")
async def get_project_analytics():
    """Returns per-project performance metrics including contract value, workforce, and site progress."""
    return await _get_service().get_project_analytics()


@router.get("/workforce")
async def get_workforce_analytics():
    """Returns workforce utilization analytics: top assigned employees, utilization rates, avg duration."""
    return await _get_service().get_workforce_analytics()


@router.get("/external-workers")
async def get_external_worker_analytics():
    """Returns external worker usage statistics and cost breakdown per project."""
    return await _get_service().get_external_worker_analytics()
