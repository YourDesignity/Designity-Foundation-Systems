"""Human resources routers."""

from backend.routers.hr.employees import router as employees_router, download_router as employees_download_router
from backend.routers.hr.attendance import router as attendance_router
from backend.routers.hr.schedules import router as schedules_router
from backend.routers.hr.designations import router as designations_router

__all__ = [
    "employees_router",
    "employees_download_router",
    "attendance_router",
    "schedules_router",
    "designations_router",
]
