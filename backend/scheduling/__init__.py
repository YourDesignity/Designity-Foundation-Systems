"""
Contract scheduling & automation engine — Phase 5E.

Exports:
    SchedulingEngine   — manages and executes scheduled jobs
    ScheduleType       — enum of all built-in schedule types
    NotificationSystem — multi-channel notification dispatcher
"""

from backend.scheduling.engine import SchedulingEngine
from backend.scheduling.notifications import NotificationChannel, NotificationSystem
from backend.scheduling.schedules import ScheduleType

__all__ = [
    "SchedulingEngine",
    "ScheduleType",
    "NotificationSystem",
    "NotificationChannel",
]
