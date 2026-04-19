"""Unit tests for the Phase 5E contract scheduling & automation system.

These tests exercise SchedulingEngine, ScheduleCreator, JobExecutor,
NotificationSystem, and the Beanie document models **without** requiring a
live MongoDB connection.  All database calls are mocked via
``unittest.mock``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.scheduling.schedules import ScheduleType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contract(
    uid: int = 1,
    contract_code: str = "CNT-TEST-001",
    state: str = "DRAFT",
    enabled_modules: list | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> MagicMock:
    """Return a lightweight mock that behaves like a Contract document."""
    now = datetime.now()
    c = MagicMock()
    c.uid = uid
    c.contract_code = contract_code
    c.workflow_state = state
    c.workflow_metadata = {}
    c.state_changed_at = None
    c.state_changed_by = None
    c.enabled_modules = enabled_modules or []
    c.project_id = 42
    c.contract_value = 5000.0
    c.created_by_admin_id = 7
    c.start_date = start_date or (now + timedelta(days=1))
    c.end_date = end_date or (now + timedelta(days=365))
    c.save = AsyncMock()
    return c


def _make_job(
    job_type: str = "contract_activation",
    target_id: int = 1,
    status: str = "PENDING",
    retry_count: int = 0,
    max_retries: int = 3,
    scheduled_for: datetime | None = None,
    payload: dict | None = None,
) -> MagicMock:
    """Return a mock ScheduledJob document."""
    job = MagicMock()
    job.id = "507f1f77bcf86cd799439011"
    job.job_type = job_type
    job.target_id = target_id
    job.target_type = "contract"
    job.status = status
    job.retry_count = retry_count
    job.max_retries = max_retries
    job.scheduled_for = scheduled_for or datetime.now()
    job.payload = payload or {}
    job.last_error = None
    job.completed_at = None
    job.save = AsyncMock()
    return job


# ===========================================================================
# ScheduledJob model
# ===========================================================================


class TestScheduledJobModel:
    def test_model_has_required_fields(self):
        from backend.models.schedules import ScheduledJob

        fields = ScheduledJob.model_fields
        for field in (
            "job_type",
            "target_type",
            "target_id",
            "scheduled_for",
            "status",
            "retry_count",
            "max_retries",
            "last_error",
            "payload",
            "created_at",
            "updated_at",
            "completed_at",
        ):
            assert field in fields, f"ScheduledJob missing field: {field}"

    def test_default_status_is_pending(self):
        from backend.models.schedules import ScheduledJob

        assert ScheduledJob.model_fields["status"].default == "PENDING"

    def test_default_retry_count_is_zero(self):
        from backend.models.schedules import ScheduledJob

        assert ScheduledJob.model_fields["retry_count"].default == 0

    def test_default_max_retries_is_three(self):
        from backend.models.schedules import ScheduledJob

        assert ScheduledJob.model_fields["max_retries"].default == 3


# ===========================================================================
# NotificationLog model
# ===========================================================================


class TestNotificationLogModel:
    def test_model_has_required_fields(self):
        from backend.models.schedules import NotificationLog

        fields = NotificationLog.model_fields
        for field in (
            "notification_type",
            "recipient_type",
            "recipient_id",
            "channel",
            "subject",
            "body",
            "sent_at",
            "status",
            "error",
            "metadata",
        ):
            assert field in fields, f"NotificationLog missing field: {field}"

    def test_default_status_is_pending(self):
        from backend.models.schedules import NotificationLog

        assert NotificationLog.model_fields["status"].default == "PENDING"


# ===========================================================================
# RecurringSchedule model
# ===========================================================================


class TestRecurringScheduleModel:
    def test_model_has_required_fields(self):
        from backend.models.schedules import RecurringSchedule

        fields = RecurringSchedule.model_fields
        for field in (
            "name",
            "description",
            "schedule_type",
            "cron_expression",
            "job_type",
            "enabled",
            "last_run",
            "next_run",
            "payload",
            "created_at",
        ):
            assert field in fields, f"RecurringSchedule missing field: {field}"

    def test_default_enabled_is_true(self):
        from backend.models.schedules import RecurringSchedule

        assert RecurringSchedule.model_fields["enabled"].default is True


# ===========================================================================
# ScheduleType enum
# ===========================================================================


class TestScheduleTypeEnum:
    def test_all_expected_values_present(self):
        expected = {
            "contract_activation",
            "contract_expiry_warning_30",
            "contract_expiry_warning_15",
            "contract_expiry_warning_7",
            "contract_auto_completion",
            "monthly_cost_calculation",
            "renewal_request",
            "payment_reminder",
        }
        actual = {st.value for st in ScheduleType}
        assert expected == actual


# ===========================================================================
# ScheduleCreator
# ===========================================================================


class TestScheduleCreatorCreateContractSchedules:
    @pytest.mark.asyncio
    async def test_creates_five_or_more_jobs_for_standard_contract(self):
        """A contract with a future start_date and end_date > 60 days away gets 6 jobs."""
        from backend.scheduling.schedules import ScheduleCreator

        now = datetime.now()
        contract = _make_contract(
            start_date=now + timedelta(days=5),
            end_date=now + timedelta(days=365),
        )

        with patch(
            "backend.scheduling.engine.SchedulingEngine.schedule_job",
            new=AsyncMock(return_value="mock-job-id"),
        ):
            job_ids = await ScheduleCreator.create_contract_schedules(contract)

        # Activation + 3 warnings + completion + renewal = 6
        assert len(job_ids) >= 5

    @pytest.mark.asyncio
    async def test_no_activation_job_when_start_date_is_past(self):
        from backend.scheduling.schedules import ScheduleCreator

        now = datetime.now()
        contract = _make_contract(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=365),
        )

        schedule_calls = []

        async def mock_schedule(job_type, **kwargs):
            schedule_calls.append(job_type)
            return "mock-job-id"

        with patch("backend.scheduling.engine.SchedulingEngine.schedule_job", side_effect=mock_schedule):
            await ScheduleCreator.create_contract_schedules(contract)

        job_type_values = [jt.value if hasattr(jt, "value") else jt for jt in schedule_calls]
        assert ScheduleType.CONTRACT_ACTIVATION.value not in job_type_values

    @pytest.mark.asyncio
    async def test_no_renewal_job_when_end_date_within_60_days(self):
        from backend.scheduling.schedules import ScheduleCreator

        now = datetime.now()
        contract = _make_contract(
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=30),
        )

        schedule_calls = []

        async def mock_schedule(job_type, **kwargs):
            schedule_calls.append(job_type)
            return "mock-job-id"

        with patch("backend.scheduling.engine.SchedulingEngine.schedule_job", side_effect=mock_schedule):
            await ScheduleCreator.create_contract_schedules(contract)

        job_type_values = [jt.value if hasattr(jt, "value") else jt for jt in schedule_calls]
        assert ScheduleType.RENEWAL_REQUEST.value not in job_type_values


class TestScheduleCreatorCancelContractSchedules:
    @pytest.mark.asyncio
    async def test_cancels_all_pending_jobs(self):
        from backend.scheduling.schedules import ScheduleCreator

        mock_job1 = _make_job(status="PENDING")
        mock_job2 = _make_job(status="PENDING")

        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[mock_job1, mock_job2])

        with patch("backend.models.schedules.ScheduledJob") as MockDoc:
            MockDoc.find.return_value = mock_query
            MockDoc.target_id = MagicMock()
            MockDoc.status = MagicMock()

            cancelled = await ScheduleCreator.cancel_contract_schedules(contract_id=1)

        assert cancelled == 2
        assert mock_job1.status == "CANCELLED"
        assert mock_job2.status == "CANCELLED"
        mock_job1.save.assert_awaited_once()
        mock_job2.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_zero_on_db_error(self):
        from backend.scheduling.schedules import ScheduleCreator

        with patch(
            "backend.models.schedules.ScheduledJob",
            side_effect=Exception("DB error"),
        ):
            cancelled = await ScheduleCreator.cancel_contract_schedules(contract_id=99)

        assert cancelled == 0


# ===========================================================================
# SchedulingEngine
# ===========================================================================


class TestSchedulingEngineScheduleJob:
    @pytest.mark.asyncio
    async def test_creates_job_and_returns_id(self):
        from backend.scheduling.engine import SchedulingEngine

        mock_job = MagicMock()
        mock_job.id = "507f1f77bcf86cd799439011"
        mock_job.insert = AsyncMock()

        with patch("backend.scheduling.engine.ScheduledJob", return_value=mock_job):
            job_id = await SchedulingEngine.schedule_job(
                job_type=ScheduleType.CONTRACT_ACTIVATION,
                target_id=1,
                scheduled_for=datetime.now() + timedelta(days=1),
                payload={"contract_id": 1},
            )

        mock_job.insert.assert_awaited_once()
        assert job_id == "507f1f77bcf86cd799439011"

    @pytest.mark.asyncio
    async def test_accepts_string_job_type(self):
        from backend.scheduling.engine import SchedulingEngine

        mock_job = MagicMock()
        mock_job.id = "abc123"
        mock_job.insert = AsyncMock()

        with patch("backend.scheduling.engine.ScheduledJob", return_value=mock_job):
            job_id = await SchedulingEngine.schedule_job(
                job_type="custom_job",
                target_id=5,
                scheduled_for=datetime.now() + timedelta(hours=2),
            )

        assert job_id == "abc123"


class TestSchedulingEngineCancelJob:
    @pytest.mark.asyncio
    async def test_cancel_job_updates_status(self):
        from backend.scheduling.engine import SchedulingEngine

        mock_job = _make_job(status="PENDING")

        with (
            patch("backend.scheduling.engine.PydanticObjectId", return_value="oid"),
            patch("backend.scheduling.engine.ScheduledJob") as MockDoc,
        ):
            MockDoc.get = AsyncMock(return_value=mock_job)
            success = await SchedulingEngine.cancel_job("507f1f77bcf86cd799439011")

        assert success is True
        assert mock_job.status == "CANCELLED"
        mock_job.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_job_returns_false_when_not_found(self):
        from backend.scheduling.engine import SchedulingEngine

        with (
            patch("backend.scheduling.engine.PydanticObjectId", return_value="oid"),
            patch("backend.scheduling.engine.ScheduledJob") as MockDoc,
        ):
            MockDoc.get = AsyncMock(return_value=None)
            success = await SchedulingEngine.cancel_job("nonexistent")

        assert success is False


class TestSchedulingEngineProcessDueJobs:
    @pytest.mark.asyncio
    async def test_processes_due_jobs_and_marks_completed(self):
        from backend.scheduling.engine import SchedulingEngine

        due_job = _make_job(
            job_type="contract_activation",
            scheduled_for=datetime.now() - timedelta(minutes=1),
        )

        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[due_job])

        with (
            patch("backend.scheduling.engine.ScheduledJob") as MockDoc,
            patch(
                "backend.scheduling.engine.SchedulingEngine._execute_job",
                new=AsyncMock(),
            ),
        ):
            MockDoc.find.return_value = mock_query
            MockDoc.status = MagicMock()
            MockDoc.scheduled_for = MagicMock()
            MockDoc.scheduled_for.__le__ = MagicMock(return_value=MagicMock())

            summary = await SchedulingEngine.process_due_jobs()

        assert summary["executed"] == 1
        assert summary["succeeded"] == 1
        assert due_job.status == "COMPLETED"
        assert due_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_retry_logic_on_first_failure(self):
        from backend.scheduling.engine import SchedulingEngine

        failing_job = _make_job(
            job_type="contract_activation",
            retry_count=0,
            max_retries=3,
        )

        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[failing_job])

        with (
            patch("backend.scheduling.engine.ScheduledJob") as MockDoc,
            patch(
                "backend.scheduling.engine.SchedulingEngine._execute_job",
                new=AsyncMock(side_effect=RuntimeError("transient error")),
            ),
        ):
            MockDoc.find.return_value = mock_query
            MockDoc.status = MagicMock()
            MockDoc.scheduled_for = MagicMock()
            MockDoc.scheduled_for.__le__ = MagicMock(return_value=MagicMock())

            summary = await SchedulingEngine.process_due_jobs()

        assert summary["retried"] == 1
        assert failing_job.status == "PENDING"  # Re-queued for retry
        assert failing_job.retry_count == 1
        assert failing_job.last_error == "transient error"

    @pytest.mark.asyncio
    async def test_job_marked_failed_after_max_retries(self):
        from backend.scheduling.engine import SchedulingEngine

        exhausted_job = _make_job(
            job_type="contract_activation",
            retry_count=2,
            max_retries=3,
        )

        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[exhausted_job])

        with (
            patch("backend.scheduling.engine.ScheduledJob") as MockDoc,
            patch(
                "backend.scheduling.engine.SchedulingEngine._execute_job",
                new=AsyncMock(side_effect=RuntimeError("permanent error")),
            ),
        ):
            MockDoc.find.return_value = mock_query
            MockDoc.status = MagicMock()
            MockDoc.scheduled_for = MagicMock()
            MockDoc.scheduled_for.__le__ = MagicMock(return_value=MagicMock())

            summary = await SchedulingEngine.process_due_jobs()

        assert summary["failed"] == 1
        assert exhausted_job.status == "FAILED"

    @pytest.mark.asyncio
    async def test_returns_error_key_on_db_failure(self):
        from backend.scheduling.engine import SchedulingEngine

        with patch(
            "backend.scheduling.engine.ScheduledJob",
            side_effect=Exception("connection error"),
        ):
            summary = await SchedulingEngine.process_due_jobs()

        assert "error" in summary


# ===========================================================================
# JobExecutor
# ===========================================================================


class TestJobExecutorContractActivation:
    @pytest.mark.asyncio
    async def test_activates_draft_contract(self):
        from backend.scheduling.jobs import JobExecutor

        contract = _make_contract(state="DRAFT")
        transition_mock = AsyncMock(return_value={"success": True})

        with (
            patch("backend.scheduling.jobs.JobExecutor._load_contract", new=AsyncMock(return_value=contract)),
            patch("backend.scheduling.jobs.WorkflowEngine.transition", transition_mock),
            patch("backend.scheduling.jobs.NotificationSystem.send_notification", new=AsyncMock()),
        ):
            result = await JobExecutor.execute_contract_activation(contract_id=1)

        transition_mock.assert_awaited_once()
        assert result["success"] is True


# ===========================================================================
# NotificationSystem
# ===========================================================================


class TestNotificationSystemSendNotification:
    @pytest.mark.asyncio
    async def test_creates_notification_log(self):
        from backend.scheduling.notifications import NotificationSystem

        mock_log = MagicMock()
        mock_log.id = "log-id-123"
        mock_log.insert = AsyncMock()
        mock_log.save = AsyncMock()

        with patch("backend.scheduling.notifications.NotificationLog", return_value=mock_log):
            result = await NotificationSystem.send_notification(
                notification_type="expiry_warning",
                recipient_id=5,
                channel="in_app",
                subject="Test Subject",
                body="Test Body",
            )

        mock_log.insert.assert_awaited_once()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_routes_email_channel(self):
        from backend.scheduling.notifications import NotificationSystem

        mock_log = MagicMock()
        mock_log.id = "log-id"
        mock_log.insert = AsyncMock()
        mock_log.save = AsyncMock()
        email_mock = AsyncMock()

        with (
            patch("backend.scheduling.notifications.NotificationLog", return_value=mock_log),
            patch.object(NotificationSystem, "_send_email", email_mock),
        ):
            await NotificationSystem.send_notification(
                notification_type="test",
                recipient_id=1,
                channel="email",
                subject="Subject",
                body="Body",
            )

        email_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_routes_sms_channel(self):
        from backend.scheduling.notifications import NotificationSystem

        mock_log = MagicMock()
        mock_log.id = "log-id"
        mock_log.insert = AsyncMock()
        mock_log.save = AsyncMock()
        sms_mock = AsyncMock()

        with (
            patch("backend.scheduling.notifications.NotificationLog", return_value=mock_log),
            patch.object(NotificationSystem, "_send_sms", sms_mock),
        ):
            await NotificationSystem.send_notification(
                notification_type="test",
                recipient_id=1,
                channel="sms",
                subject="Subject",
                body="Body",
            )

        sms_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_logs_failure_on_send_error(self):
        from backend.scheduling.notifications import NotificationSystem

        mock_log = MagicMock()
        mock_log.id = "log-id"
        mock_log.insert = AsyncMock()
        mock_log.save = AsyncMock()

        with (
            patch("backend.scheduling.notifications.NotificationLog", return_value=mock_log),
            patch.object(
                NotificationSystem,
                "_send_email",
                AsyncMock(side_effect=RuntimeError("SMTP error")),
            ),
        ):
            result = await NotificationSystem.send_notification(
                notification_type="test",
                recipient_id=1,
                channel="email",
                subject="Subject",
                body="Body",
            )

        assert result["success"] is False
        assert mock_log.status == "FAILED"


class TestNotificationSystemDomainMethods:
    @pytest.mark.asyncio
    async def test_send_expiry_warning_sends_multiple_channels(self):
        from backend.scheduling.notifications import NotificationSystem

        contract = _make_contract()
        send_mock = AsyncMock(return_value={"success": True})

        with patch.object(NotificationSystem, "send_notification", send_mock):
            results = await NotificationSystem.send_expiry_warning(contract, 30)

        # Should send on at least 2 channels (email + in_app)
        assert send_mock.await_count >= 2

    @pytest.mark.asyncio
    async def test_send_renewal_reminder_uses_email(self):
        from backend.scheduling.notifications import NotificationSystem

        contract = _make_contract()
        send_mock = AsyncMock(return_value={"success": True})

        with patch.object(NotificationSystem, "send_notification", send_mock):
            await NotificationSystem.send_renewal_reminder(contract)

        assert send_mock.await_count == 1
        _, kwargs = send_mock.call_args
        assert kwargs.get("channel") == "email" or send_mock.call_args[0][2] == "email"

    @pytest.mark.asyncio
    async def test_send_completion_notification_sends_multiple_channels(self):
        from backend.scheduling.notifications import NotificationSystem

        contract = _make_contract()
        send_mock = AsyncMock(return_value={"success": True})

        with patch.object(NotificationSystem, "send_notification", send_mock):
            await NotificationSystem.send_completion_notification(contract)

        assert send_mock.await_count >= 2


# ===========================================================================
# SchedulingWorker
# ===========================================================================


class TestSchedulingWorker:
    def test_initial_state_is_not_running(self):
        from backend.scheduling.worker import SchedulingWorker

        worker = SchedulingWorker()
        assert worker.running is False

    def test_stop_sets_running_false(self):
        from backend.scheduling.worker import SchedulingWorker

        worker = SchedulingWorker()
        worker.running = True
        worker.stop()
        assert worker.running is False

    def test_default_interval_is_60(self):
        from backend.scheduling.worker import SchedulingWorker

        worker = SchedulingWorker()
        assert worker.interval_seconds == 60

    def test_custom_interval(self):
        from backend.scheduling.worker import SchedulingWorker

        worker = SchedulingWorker(interval_seconds=30)
        assert worker.interval_seconds == 30
