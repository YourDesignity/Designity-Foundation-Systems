"""Role-based labour contract routers (Phase 1)."""

from backend.routers.role_contracts.contract_roles import router as contract_roles_router
from backend.routers.role_contracts.daily_fulfillment import router as daily_fulfillment_router

__all__ = ["contract_roles_router", "daily_fulfillment_router"]
