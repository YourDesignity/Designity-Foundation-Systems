"""
Schedule type definitions and schedule creation logic for Phase 5E.

Provides:
    ScheduleType   — enum of all schedule varieties
    ScheduleCreator — factory that creates / cancels / reschedules jobs for a
                      contract
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class ScheduleType(str, Enum):
    """All built-in schedule types used by the scheduling engine."""

    CONTRACT_ACTIVATION = "contract_activation"
    CONTRACT_EXPIRY_WARNING_30 = "contract_expiry_warning_30"
    CONTRACT_EXPIRY_WARNING_15 = "contract_expiry_warning_15"
    CONTRACT_EXPIRY_WARNING_7 = "contract_expiry_warning_7"
    CONTRACT_AUTO_COMPLETION = "contract_auto_completion"
    MONTHLY_COST_CALCULATION = "monthly_cost_calculation"
    RENEWAL_REQUEST = "renewal_request"
    PAYMENT_REMINDER = "payment_reminder"


class ScheduleCreator:
    """
    Factory that creates, cancels, and reschedules ScheduledJob documents for
    a given contract.

    All methods are async so they can be awaited directly from FastAPI route
    handlers or background tasks.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    async def create_contract_schedules(contract: Any) -> List[str]:
        """
        Create all standard scheduled jobs for a newly-created contract.

        Jobs created (when applicable):
        - CONTRACT_ACTIVATION       — if start_date is in the future
        - CONTRACT_EXPIRY_WARNING_30 — 30 days before end_date
        - CONTRACT_EXPIRY_WARNING_15 — 15 days before end_date
        - CONTRACT_EXPIRY_WARNING_7  —  7 days before end_date
        - CONTRACT_AUTO_COMPLETION   — at end_date
        - RENEWAL_REQUEST            — 60 days before end_date

        Returns a list of created job IDs.
        """
        from backend.scheduling.engine import SchedulingEngine

        now = datetime.now()
        job_ids: List[str] = []
        contract_id: int = getattr(contract, "uid", 0)
        start_date: Optional[datetime] = getattr(contract, "start_date", None)
        end_date: Optional[datetime] = getattr(contract, "end_date", None)

        # 1. Auto-activation (only if start is in the future)
        if start_date and start_date > now:
            jid = await SchedulingEngine.schedule_job(
                job_type=ScheduleType.CONTRACT_ACTIVATION,
                target_id=contract_id,
                scheduled_for=start_date,
                payload={"contract_id": contract_id},
            )
            job_ids.append(jid)

        if end_date:
            # 2. Expiry warnings
            for days, stype in [
                (30, ScheduleType.CONTRACT_EXPIRY_WARNING_30),
                (15, ScheduleType.CONTRACT_EXPIRY_WARNING_15),
                (7, ScheduleType.CONTRACT_EXPIRY_WARNING_7),
            ]:
                warn_at = end_date - timedelta(days=days)
                if warn_at > now:
                    jid = await SchedulingEngine.schedule_job(
                        job_type=stype,
                        target_id=contract_id,
                        scheduled_for=warn_at,
                        payload={"contract_id": contract_id, "days_remaining": days},
                    )
                    job_ids.append(jid)

            # 3. Auto-completion at end_date
            if end_date > now:
                jid = await SchedulingEngine.schedule_job(
                    job_type=ScheduleType.CONTRACT_AUTO_COMPLETION,
                    target_id=contract_id,
                    scheduled_for=end_date,
                    payload={"contract_id": contract_id},
                )
                job_ids.append(jid)

            # 4. Renewal request 60 days before end_date
            renewal_at = end_date - timedelta(days=60)
            if renewal_at > now:
                jid = await SchedulingEngine.schedule_job(
                    job_type=ScheduleType.RENEWAL_REQUEST,
                    target_id=contract_id,
                    scheduled_for=renewal_at,
                    payload={"contract_id": contract_id},
                )
                job_ids.append(jid)

        return job_ids

    @staticmethod
    async def cancel_contract_schedules(contract_id: int) -> int:
        """
        Cancel all PENDING scheduled jobs for *contract_id*.

        Returns the number of jobs cancelled.
        """
        from backend.models.schedules import ScheduledJob

        try:
            pending_jobs = await ScheduledJob.find(
                ScheduledJob.target_id == contract_id,
                ScheduledJob.status == "PENDING",
            ).to_list()

            count = 0
            for job in pending_jobs:
                job.status = "CANCELLED"
                job.updated_at = datetime.now()
                await job.save()
                count += 1

            return count
        except Exception:  # noqa: BLE001
            return 0

    @staticmethod
    async def reschedule_contract(contract: Any) -> Dict[str, Any]:
        """
        Cancel existing pending jobs and recreate schedules when a contract's
        dates have changed.

        Returns a summary dict with ``cancelled`` and ``created`` counts.
        """
        contract_id: int = getattr(contract, "uid", 0)
        cancelled = await ScheduleCreator.cancel_contract_schedules(contract_id)
        created_ids = await ScheduleCreator.create_contract_schedules(contract)
        return {"cancelled": cancelled, "created": len(created_ids), "job_ids": created_ids}
