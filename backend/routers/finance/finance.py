import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.security import get_current_active_user
from backend.services.finance.financial_analytics_service import FinancialAnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/finance", tags=["Finance & Analytics"])
_service = FinancialAnalyticsService()


@router.get("/summary")
async def get_financial_summary(current_user: dict = Depends(get_current_active_user)):
    try:
        return await _service.get_financial_summary()
    except Exception as e:
        logger.error(f"Finance summary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced-summary")
async def get_advanced_financial_summary(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Comprehensive financial dashboard data with optional date range filtering.
    Returns: overview KPIs, monthly trends, cost breakdown, contract P&L,
             cash flow waterfall, efficiency metrics, invoice summary.
    """
    try:
        return await _service.get_advanced_financial_summary(
            date_from=date_from, date_to=date_to
        )
    except Exception as e:
        logger.error(f"Advanced finance error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
