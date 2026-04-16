"""Employee assignment routers."""

from backend.routers.assignments.assignments import router as assignments_router
from backend.routers.assignments.temporary_assignments import router as temporary_assignments_router

__all__ = ["assignments_router", "temporary_assignments_router"]
