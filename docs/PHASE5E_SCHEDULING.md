# Phase 5E — Contract Scheduling & Automation

## Overview

Phase 5E introduces a **time-based scheduling engine** that automates contract
lifecycle events, manages renewal cycles, dispatches multi-channel
notifications, and runs recurring background jobs.  It builds directly on the
Phase 5D WorkflowEngine (state transitions) and Phase 5C contract modules
(cost calculations).

---

## Architecture

```
SchedulingWorker  (polls every 60 s)
    │
    ▼
SchedulingEngine
    │
    ├─ schedule_job()         — create a one-off ScheduledJob
    ├─ cancel_job()           — cancel a pending job
    ├─ process_due_jobs()     — execute all jobs whose scheduled_for <= now
    └─ create_recurring_schedules()  — seed monthly cron-like definitions
    │
    ▼
JobExecutor  (one method per job type)
    ├─ execute_contract_activation()
    ├─ execute_expiry_warning()
    ├─ execute_auto_completion()
    ├─ execute_cost_calculation()
    ├─ execute_renewal_request()
    └─ execute_payment_reminder()
    │
    ▼
NotificationSystem
    ├─ send_notification()          — core method (creates NotificationLog)
    ├─ send_expiry_warning()
    ├─ send_renewal_reminder()
    ├─ send_payment_reminder()
    └─ send_completion_notification()
```

---

## File Layout

```
backend/
├── scheduling/
│   ├── __init__.py        # Package exports
│   ├── engine.py          # SchedulingEngine static methods
│   ├── schedules.py       # ScheduleType enum + ScheduleCreator
│   ├── jobs.py            # JobExecutor implementations
│   ├── notifications.py   # NotificationSystem + NotificationChannel
│   └── worker.py          # SchedulingWorker background loop
└── models/
    └── schedules.py       # ScheduledJob, NotificationLog, RecurringSchedule
```

---

## Schedule Types

| ScheduleType | Triggered At | Action |
|---|---|---|
| `contract_activation` | `start_date` | Transition DRAFT/PENDING → ACTIVE |
| `contract_expiry_warning_30` | `end_date - 30 days` | Email + in-app notification |
| `contract_expiry_warning_15` | `end_date - 15 days` | Email + in-app notification |
| `contract_expiry_warning_7` | `end_date - 7 days` | URGENT email + in-app notification |
| `contract_auto_completion` | `end_date` | Transition ACTIVE → COMPLETED |
| `monthly_cost_calculation` | 1st of every month | Run module.calculate_cost() for all ACTIVE contracts |
| `renewal_request` | `end_date - 60 days` | Create ApprovalRequest + notify owner |
| `payment_reminder` | 5th of every month | Send payment due notice |

---

## Database Models

### ScheduledJob

```python
class ScheduledJob(Document):
    job_type: str          # ScheduleType value
    target_type: str       # "contract" | "project"
    target_id: int         # e.g. contract.uid
    scheduled_for: datetime
    status: str            # PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str]
    payload: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
```

### NotificationLog

```python
class NotificationLog(Document):
    notification_type: str  # e.g. "expiry_warning", "renewal_reminder"
    recipient_type: str     # "user" | "admin" | "team"
    recipient_id: int
    channel: str            # "email" | "sms" | "webhook" | "in_app"
    subject: str
    body: str
    sent_at: Optional[datetime]
    status: str             # PENDING | SENT | FAILED
    error: Optional[str]
    metadata: Dict[str, Any] = {}
```

### RecurringSchedule

```python
class RecurringSchedule(Document):
    name: str
    description: str
    schedule_type: str              # "daily" | "weekly" | "monthly" | "cron"
    cron_expression: Optional[str]  # "0 9 1 * *" = 1st of month at 09:00
    job_type: str
    enabled: bool = True
    last_run: Optional[datetime]
    next_run: datetime
    payload: Dict[str, Any] = {}
    created_at: datetime
```

---

## Job Execution Flow

```
Worker tick (every 60 s)
    │
    ▼
SchedulingEngine.process_due_jobs()
    │
    ├─ SELECT ScheduledJob WHERE status=PENDING AND scheduled_for <= now
    │
    └─ For each job:
        ├─ Set status = RUNNING
        ├─ Call JobExecutor.execute_<type>(target_id, payload)
        │    ├─ SUCCESS → status = COMPLETED, completed_at = now
        │    └─ FAILURE → retry_count += 1
        │         ├─ retry_count < max_retries → status = PENDING, scheduled_for += back-off
        │         └─ retry_count >= max_retries → status = FAILED
        └─ Save updated job
```

---

## Notification Channels

| Channel | Value | Description |
|---|---|---|
| Email | `email` | Sent via `_send_email()` stub (SMTP/SendGrid/SES) |
| SMS | `sms` | Sent via `_send_sms()` stub (Twilio/AWS SNS) |
| Webhook | `webhook` | POSTed via `_send_webhook()` stub (httpx) |
| In-App | `in_app` | Stored in NotificationLog, consumed by the frontend |

Replace the `_send_*` private methods in `notifications.py` with real provider
integrations when ready.

---

## Background Worker Setup

### Starting the Worker

```python
# In main.py lifespan or a standalone script
import asyncio
from backend.scheduling.worker import SchedulingWorker

worker = SchedulingWorker(interval_seconds=60)

# Inside FastAPI lifespan
asyncio.create_task(worker.start())

# Stopping gracefully
worker.stop()
```

### Running as a Standalone Process

```bash
python -c "
import asyncio
from backend.scheduling.worker import SchedulingWorker

async def main():
    worker = SchedulingWorker(interval_seconds=60)
    await worker.start()

asyncio.run(main())
"
```

---

## Creating Custom Schedules

### One-Off Job

```python
from backend.scheduling import SchedulingEngine, ScheduleType
from datetime import datetime, timedelta

# Schedule a contract activation 5 days from now
job_id = await SchedulingEngine.schedule_job(
    job_type=ScheduleType.CONTRACT_ACTIVATION,
    target_id=contract.uid,
    scheduled_for=datetime.now() + timedelta(days=5),
    payload={"contract_id": contract.uid},
)
```

### Cancelling a Job

```python
success = await SchedulingEngine.cancel_job(job_id)
```

### Creating All Schedules for a New Contract

```python
from backend.scheduling.schedules import ScheduleCreator

# Called automatically after contract creation
job_ids = await ScheduleCreator.create_contract_schedules(contract)
# Returns list of created job IDs

# Cancel all pending schedules for a contract
cancelled = await ScheduleCreator.cancel_contract_schedules(contract.uid)

# Reschedule after date change
result = await ScheduleCreator.reschedule_contract(contract)
# {"cancelled": 5, "created": 6, "job_ids": [...]}
```

---

## Monitoring Scheduled Jobs

```python
from backend.models.schedules import ScheduledJob, NotificationLog

# Pending jobs
pending = await ScheduledJob.find(ScheduledJob.status == "PENDING").to_list()

# Failed jobs
failed = await ScheduledJob.find(ScheduledJob.status == "FAILED").to_list()

# Notifications for a specific contract
notifications = await NotificationLog.find(
    NotificationLog.metadata.contract_id == contract_id
).to_list()
```

---

## Integration with Phase 5D Workflow

Phase 5E calls `WorkflowEngine.transition()` for:

- **Auto-activation**: DRAFT/PENDING_APPROVAL → ACTIVE
- **Auto-completion**: ACTIVE → COMPLETED

```python
# Inside JobExecutor.execute_contract_activation
result = await WorkflowEngine.transition(
    contract=contract,
    target_state=ContractState.ACTIVE,
    reason="Automated activation on start_date",
)
```

Approval requests for renewals are created via `ApprovalSystem`:

```python
# Inside JobExecutor.execute_renewal_request
await ApprovalSystem.create_approval_request(
    contract=contract,
    approval_type=ApprovalType.CONTRACT_ACTIVATION,
    requested_by=contract.created_by_admin_id,
    required_approvers=[contract.created_by_admin_id],
)
```

---

## Integration with Phase 5C Modules

Monthly cost calculations call `module.calculate_cost()` for every enabled
module on every ACTIVE contract:

```python
# Inside JobExecutor.execute_cost_calculation
module = ModuleRegistry.get_module(module_name)
result = await module.calculate_cost(contract, month, year)
# {"module": "employee", "total_cost": 5000.0, "breakdown": {...}}
```

Results are persisted in `contract.workflow_metadata["cost_{year}_{month}"]`.

---

## Example: Full Contract Lifecycle Automation

```python
from datetime import datetime, timedelta
from backend.scheduling.schedules import ScheduleCreator

# 1. Create a contract with future dates
contract.start_date = datetime.now() + timedelta(days=30)
contract.end_date   = datetime.now() + timedelta(days=365)
await contract.save()

# 2. Create all lifecycle schedules
job_ids = await ScheduleCreator.create_contract_schedules(contract)
# Creates: activation, 3 expiry warnings, auto-completion, renewal_request = 6 jobs

# 3. Worker runs every minute and processes due jobs automatically
# Day 30:  CONTRACT_ACTIVATION fires    → contract becomes ACTIVE
# Day 275: RENEWAL_REQUEST fires        → approval request created, owner notified
# Day 305: CONTRACT_EXPIRY_WARNING_30   → email + in-app to owner
# Day 320: CONTRACT_EXPIRY_WARNING_15   → email + in-app to owner
# Day 328: CONTRACT_EXPIRY_WARNING_7    → URGENT email + in-app
# Day 335: CONTRACT_AUTO_COMPLETION     → contract transitions to COMPLETED
```

---

## Recurring Schedules (Monthly Jobs)

The built-in recurring schedules are seeded by calling:

```python
await SchedulingEngine.create_recurring_schedules()
```

| Name | Cron | Description |
|---|---|---|
| `monthly_cost_calculation` | `0 1 1 * *` | 1st of month at 01:00 |
| `payment_reminders` | `0 9 5 * *` | 5th of month at 09:00 |
| `monthly_report_generation` | `0 23 28 * *` | 28th of month at 23:00 |

---

## Troubleshooting Failed Jobs

### Viewing Failed Jobs

```python
from backend.models.schedules import ScheduledJob

failed = await ScheduledJob.find(ScheduledJob.status == "FAILED").to_list()
for job in failed:
    print(f"Job {job.id}: {job.job_type} for contract {job.target_id}")
    print(f"  Error: {job.last_error}")
    print(f"  Retries: {job.retry_count}/{job.max_retries}")
```

### Manually Retrying a Job

```python
job.status = "PENDING"
job.retry_count = 0
job.scheduled_for = datetime.now()
await job.save()
# Worker will pick it up on the next tick
```

### Common Issues

| Problem | Cause | Fix |
|---|---|---|
| Job stays PENDING | Worker not running | Start `SchedulingWorker` |
| Job keeps failing | Contract not found | Verify contract uid exists |
| Activation skipped | Contract not in DRAFT/PENDING | Check current `workflow_state` |
| Completion skipped | Contract not ACTIVE | Verify contract is ACTIVE |
| Notification FAILED | Provider not configured | Implement `_send_email` / `_send_sms` stubs |

---

## Expected Outcomes

| # | Outcome |
|---|---------|
| 1 | Automated contract activation on `start_date` |
| 2 | Multi-level expiry warnings (30/15/7 days) |
| 3 | Auto-completion on `end_date` |
| 4 | Renewal workflow with ApprovalSystem integration |
| 5 | Monthly cost calculation via Phase 5C modules |
| 6 | Multi-channel notification system (email/SMS/webhook/in-app) |
| 7 | Background worker with exponential back-off retry (max 3 attempts) |
| 8 | Comprehensive test coverage without live MongoDB |
| 9 | Full documentation with examples |

---

## Future Phases

- **Webhooks** — replace `_send_webhook()` stub with real HTTP client
- **Email Templates** — HTML email templates for each notification type
- **Escalation Rules** — auto-escalate pending approvals after N days
- **Dashboard** — UI to monitor scheduled jobs and notification history
