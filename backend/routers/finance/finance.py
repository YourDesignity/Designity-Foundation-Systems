import logging
from fastapi import APIRouter, HTTPException

from backend.services.finance.financial_analytics_service import FinancialAnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["Finance & Analytics"])

_service = FinancialAnalyticsService()


@router.get("/summary")
async def get_financial_summary():
    try:
        return await _service.get_financial_summary()
    except AttributeError as e:
        logger.error(f"Finance summary calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Financial calculation error: Invalid data structure"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected finance summary error: {e}")
        raise HTTPException(status_code=500, detail="Financial data error")


@router.get("/advanced-summary")
async def get_advanced_financial_summary():
    """
    Returns comprehensive financial analytics for the enhanced dashboard:
    - Monthly trends (last 6 months)
    - Detailed cost breakdown (6 categories)
    - Per-contract profitability analysis
    - Cash flow waterfall data
    - Efficiency metrics
    - At-risk contract alerts
    """
    try:
        return await _service.get_advanced_financial_summary()
    except AttributeError as e:
        logger.error(f"Finance calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Financial calculation error: Invalid data structure"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected finance error: {e}")
        raise HTTPException(status_code=500, detail="Financial data error")