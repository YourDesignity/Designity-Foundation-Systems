"""Materials and procurement routers."""

from backend.routers.materials.materials import (
    router as materials_router,
    suppliers_router,
    purchase_orders_router,
)

__all__ = ["materials_router", "suppliers_router", "purchase_orders_router"]
