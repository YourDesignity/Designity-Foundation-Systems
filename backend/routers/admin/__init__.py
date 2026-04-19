"""Admin and manager routers."""

from backend.routers.admin.admins import router as admins_router
from backend.routers.admin.managers import router as managers_router
from backend.routers.admin.manager_attendance import router as manager_attendance_router

__all__ = ["admins_router", "managers_router", "manager_attendance_router"]
