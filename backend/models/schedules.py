"""Beanie documents for the Phase 5E scheduling & automation system."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import Field


class ScheduledJob(Document):
    """
    Represents a single scheduled task that will be executed by the worker at
    a specific point in time.

    Lifecycle: PENDING → RUNNING → COMPLETED | FAILED
    Failed jobs are retried up to *max_retries* times before being abandoned.
    """

    job_type: str  # e.g. "contract_activation", "expiry_warning", …
    target_type: str = "contract"  # "contract" | "project" | …
    target_id: int  # e.g. contract.uid
    scheduled_for: datetime
    status: str = "PENDING"  # PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    class Settings:
        name = "scheduled_jobs"
        indexes = [
            "job_type",
            "target_id",
            "scheduled_for",
            "status",
            "created_at",
        ]


class NotificationLog(Document):
    """
    Immutable audit record for every notification dispatched by the system,
    regardless of channel (email, SMS, webhook, in-app).
    """

    notification_type: str  # e.g. "expiry_warning", "renewal_reminder", …
    recipient_type: str = "user"  # "user" | "admin" | "team"
    recipient_id: int
    channel: str  # "email" | "sms" | "webhook" | "in_app"
    subject: str
    body: str
    sent_at: Optional[datetime] = None
    status: str = "PENDING"  # PENDING | SENT | FAILED
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "notification_logs"
        indexes = [
            "notification_type",
            "recipient_id",
            "channel",
            "status",
            "sent_at",
        ]


class RecurringSchedule(Document):
    """
    Cron-like definition for jobs that repeat on a regular cadence.

    *cron_expression* uses standard 5-field cron syntax
    (minute hour day-of-month month day-of-week).
    When *schedule_type* is ``"daily"``, ``"weekly"``, or ``"monthly"`` the
    engine derives *next_run* automatically; ``"cron"`` requires an explicit
    *cron_expression*.
    """

    name: str
    description: str = ""
    schedule_type: str  # "daily" | "weekly" | "monthly" | "cron"
    cron_expression: Optional[str] = None  # e.g. "0 9 1 * *" = 1st of month 9am
    job_type: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "recurring_schedules"
        indexes = [
            "job_type",
            "schedule_type",
            "enabled",
            "next_run",
        ]
