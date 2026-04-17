# backend/routers/workforce_analytics.py

from fastapi import APIRouter, Depends
from backend.security import get_current_active_user

router = APIRouter(
    prefix="/workforce",
    tags=["Workforce Analytics"],
    dependencies=[Depends(get_current_active_user)],
)


def _get_service():
    from backend.services.workforce_analytics_service import WorkforceAnalyticsService
    return WorkforceAnalyticsService()


@router.get("/allocation")
async def get_workforce_allocation():
    """Returns workforce allocation data grouped by project/site."""
    return await _get_service().get_workforce_allocation()


@router.get("/utilization")
async def get_workforce_utilization():
    """Returns workforce utilization data for charts (pie chart, bar chart, trend)."""
    return await _get_service().get_workforce_utilization()
