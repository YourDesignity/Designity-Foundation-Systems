"""
Core scheduling engine for Phase 5E.

Provides SchedulingEngine, a static-method facade for:
- Creating one-off scheduled jobs
- Cancelling jobs
- Processing all due jobs (called by the background worker)
- Seeding recurring schedule definitions
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from backend.models.schedules import RecurringSchedule, ScheduledJob


class SchedulingEngine:
    """
    Static-method facade for the Phase 5E scheduling system.

    All public methods are ``async`` so they integrate seamlessly with FastAPI
    and the SchedulingWorker event loop.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    async def schedule_job(
        job_type: Any,
        target_id: int,
        scheduled_for: datetime,
        payload: Optional[Dict[str, Any]] = None,
        target_type: str = "contract",
        max_retries: int = 3,
    ) -> str:
        """
        Create a new PENDING ScheduledJob document and return its string id.
        """
        job_type_value = job_type.value if hasattr(job_type, "value") else str(job_type)

        job = ScheduledJob(
            job_type=job_type_value,
            target_type=target_type,
            target_id=target_id,
            scheduled_for=scheduled_for,
            status="PENDING",
            payload=payload or {},
            max_retries=max_retries,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await job.insert()
        return str(job.id)

    @staticmethod
    async def cancel_job(job_id: str) -> bool:
        """
        Mark a single job as CANCELLED by its document id.

        Returns True if the job was found and cancelled, False otherwise.
        """
        try:
            oid = PydanticObjectId(job_id)
            job = await ScheduledJob.get(oid)
            if job is None:
                return False
            job.status = "CANCELLED"
            job.updated_at = datetime.now()
            await job.save()
            return True
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    async def process_due_jobs() -> Dict[str, Any]:
        """
        Query all PENDING jobs whose scheduled_for <= now, execute them, and
        update their status.

        Failed jobs are retried if retry_count < max_retries; otherwise they
        are left in FAILED state.

        Returns a summary dict with executed/succeeded/failed counts.
        """
        now = datetime.now()
        summary = {"executed": 0, "succeeded": 0, "failed": 0, "retried": 0}

        try:
            due_jobs: List[ScheduledJob] = await ScheduledJob.find(
                ScheduledJob.status == "PENDING",
                ScheduledJob.scheduled_for <= now,
            ).to_list()
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc), **summary}

        for job in due_jobs:
            summary["executed"] += 1

            # Mark as running
            job.status = "RUNNING"
            job.updated_at = datetime.now()
            try:
                await job.save()
            except Exception:  # noqa: BLE001
                pass

            try:
                await SchedulingEngine._execute_job(job)
                job.status = "COMPLETED"
                job.completed_at = datetime.now()
                summary["succeeded"] += 1
            except Exception as exc:  # noqa: BLE001
                job.retry_count += 1
                job.last_error = str(exc)
                if job.retry_count < job.max_retries:
                    # Re-queue for retry with a short back-off
                    job.status = "PENDING"
                    job.scheduled_for = datetime.now() + timedelta(minutes=5 * job.retry_count)
                    summary["retried"] += 1
                else:
                    job.status = "FAILED"
                    summary["failed"] += 1

            job.updated_at = datetime.now()
            try:
                await job.save()
            except Exception:  # noqa: BLE001
                pass

        return summary

    @staticmethod
    async def create_recurring_schedules() -> List[str]:
        """
        Seed the built-in recurring schedule definitions if they do not already
        exist.

        Creates:
        - Monthly cost calculation on the 1st of each month at 01:00
        - Payment reminders on the 5th of each month at 09:00
        - Report generation on the last day of each month at 23:00
        """
        now = datetime.now()
        created: List[str] = []

        definitions = [
            {
                "name": "monthly_cost_calculation",
                "description": "Calculate costs for all active contracts on the 1st of every month.",
                "schedule_type": "monthly",
                "cron_expression": "0 1 1 * *",
                "job_type": "monthly_cost_calculation",
                "next_run": SchedulingEngine._next_monthly(now, day=1, hour=1),
            },
            {
                "name": "payment_reminders",
                "description": "Send payment reminders on the 5th of every month.",
                "schedule_type": "monthly",
                "cron_expression": "0 9 5 * *",
                "job_type": "payment_reminder",
                "next_run": SchedulingEngine._next_monthly(now, day=5, hour=9),
            },
            {
                "name": "monthly_report_generation",
                "description": "Generate progress reports on the last day of every month.",
                "schedule_type": "monthly",
                "cron_expression": "0 23 28 * *",
                "job_type": "report_generation",
                "next_run": SchedulingEngine._next_monthly(now, day=28, hour=23),
            },
        ]

        for defn in definitions:
            try:
                existing = await RecurringSchedule.find_one(
                    RecurringSchedule.name == defn["name"]
                )
                if existing is not None:
                    continue
                schedule = RecurringSchedule(**defn, created_at=now)
                await schedule.insert()
                created.append(defn["name"])
            except Exception:  # noqa: BLE001
                pass

        return created

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _execute_job(job: Any) -> None:
        """Dispatch a ScheduledJob to the appropriate JobExecutor method."""
        from backend.scheduling.jobs import JobExecutor

        jtype: str = job.job_type
        tid: int = job.target_id
        payload: Dict[str, Any] = job.payload or {}

        if jtype == "contract_activation":
            await JobExecutor.execute_contract_activation(tid, payload)
        elif jtype in (
            "contract_expiry_warning_30",
            "contract_expiry_warning_15",
            "contract_expiry_warning_7",
        ):
            days = int(jtype.rsplit("_", 1)[-1])
            await JobExecutor.execute_expiry_warning(tid, days, payload)
        elif jtype == "contract_auto_completion":
            await JobExecutor.execute_auto_completion(tid, payload)
        elif jtype == "monthly_cost_calculation":
            month = payload.get("month", datetime.now().month)
            year = payload.get("year", datetime.now().year)
            await JobExecutor.execute_cost_calculation(tid, month, year, payload)
        elif jtype == "renewal_request":
            await JobExecutor.execute_renewal_request(tid, payload)
        elif jtype == "payment_reminder":
            await JobExecutor.execute_payment_reminder(tid, payload)
        else:
            raise ValueError(f"Unknown job_type: '{jtype}'")

    @staticmethod
    def _next_monthly(now: datetime, day: int, hour: int) -> datetime:
        """Return the next occurrence of a specific day/hour in a monthly cycle."""
        candidate = now.replace(day=day, hour=hour, minute=0, second=0, microsecond=0)
        if candidate <= now:
            # Move to next month
            if now.month == 12:
                candidate = candidate.replace(year=now.year + 1, month=1)
            else:
                candidate = candidate.replace(month=now.month + 1)
        return candidate
