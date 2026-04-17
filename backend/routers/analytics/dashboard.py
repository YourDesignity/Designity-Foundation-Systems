# backend/routers/dashboard.py

from fastapi import APIRouter, Depends
from backend.security import get_current_active_user, require_permission

router = APIRouter(
    prefix="/dashboard",
    tags=["System Dashboard"]
)


def _get_service():
    from backend.services.analytics.dashboard_service import DashboardService
    return DashboardService()


@router.get("/stats")
async def get_system_stats():
    """Returns counts of all major collections for the UI cards."""
    return await _get_service().get_system_stats()


@router.get("/system_health")
async def get_system_health():
    """Returns Server RAM/CPU usage."""
    return await _get_service().get_system_health()


@router.get("/schema_graph")
async def get_schema_visualization():
    """Defines the nodes and edges for the Graph."""
    return await _get_service().get_schema_visualization()


@router.get("/logs/live")
async def get_live_logs():
    """Reads the last 50 lines of the main app log."""
    return await _get_service().get_live_logs()


@router.get("/summary", dependencies=[Depends(get_current_active_user)])
async def get_dashboard_summary():
    """Returns a comprehensive dashboard summary for the Phase 6 overview page."""
    return await _get_service().get_comprehensive_summary()


@router.get("/workflow-summary", dependencies=[Depends(get_current_active_user)])
async def get_workflow_summary():
    """Returns aggregate statistics for the Workflow Overview dashboard."""
    return await _get_service().get_workflow_summary()


@router.get("/profit-loss", dependencies=[Depends(require_permission("finance:view"))])
async def get_profit_loss_summary():
    """Returns comprehensive profit & loss analytics."""
    return await _get_service().get_profit_loss_summary()