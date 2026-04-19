# Phase 5D — Contract Workflow Engine

## Overview

Phase 5D introduces a **workflow orchestration engine** that manages the full
contract lifecycle, coordinates Phase 5C module activation, and automates
business processes through a structured state machine.

---

## Architecture

```
WorkflowEngine
    │
    ▼ manages
ContractState (enum)
    ├── DRAFT
    ├── PENDING_APPROVAL
    ├── ACTIVE          ◄─ modules initialized
    ├── SUSPENDED
    ├── COMPLETED       ◄─ modules cleaned up  (terminal)
    └── CANCELLED       ◄─ modules cleaned up  (terminal)

    │
    ▼ triggers
StateHandler (per state)
    ├── on_enter()  — actions when entering state
    ├── on_exit()   — actions when leaving state
    ├── validate()  — checks contract meets state requirements
    └── get_allowed_transitions() — declares reachable next states

    │
    ▼ produces
WorkflowHistory  — immutable audit record
WorkflowEvent    — event log
```

---

## File Layout

```
backend/
├── workflows/
│   ├── __init__.py      # Package exports
│   ├── states.py        # ContractState enum + StateHandlers
│   ├── engine.py        # WorkflowEngine static methods
│   ├── approvals.py     # ApprovalSystem
│   └── events.py        # EventDispatcher + WorkflowEventType
└── models/
    └── workflow_history.py  # WorkflowHistory, ApprovalRequest, WorkflowEvent
```

---

## State Diagram

```
         ┌──────────────────────────────────────┐
         │                                      │
         ▼                                      │ DRAFT ◄──┐
      DRAFT ──► PENDING_APPROVAL ──► ACTIVE     │           │
        │              │               │        │  reject   │
        │         (rejected)      SUSPENDED     │           │
        │              │               │        └──────────-┘
        ▼              ▼               ▼
    CANCELLED      CANCELLED      COMPLETED
                                  CANCELLED
```

### Transition Rules

| From               | To                 | Trigger                          |
|--------------------|--------------------|----------------------------------|
| DRAFT              | PENDING_APPROVAL   | Submit for review                |
| DRAFT              | CANCELLED          | Manual cancellation              |
| PENDING_APPROVAL   | ACTIVE             | All approvals received           |
| PENDING_APPROVAL   | DRAFT              | Returned for revision            |
| PENDING_APPROVAL   | CANCELLED          | Rejection / cancellation         |
| ACTIVE             | SUSPENDED          | Temporary pause                  |
| ACTIVE             | COMPLETED          | Successful completion            |
| ACTIVE             | CANCELLED          | Early termination                |
| SUSPENDED          | ACTIVE             | Resume                           |
| SUSPENDED          | CANCELLED          | Cancellation while paused        |
| COMPLETED          | *(none)*           | Terminal state                   |
| CANCELLED          | *(none)*           | Terminal state                   |

---

## WorkflowEngine

```python
from backend.workflows import WorkflowEngine, ContractState

# Transition a contract to PENDING_APPROVAL
result = await WorkflowEngine.transition(
    contract=contract,
    target_state=ContractState.PENDING_APPROVAL,
    changed_by=admin_uid,
    reason="Ready for budget approval",
)
# result = {"success": True, "from_state": "DRAFT", "to_state": "PENDING_APPROVAL", ...}

# List available next states
transitions = WorkflowEngine.get_available_transitions(contract)
# [<ContractState.ACTIVE: 'ACTIVE'>, <ContractState.DRAFT: 'DRAFT'>, ...]

# Validate the contract satisfies current state requirements
validation = WorkflowEngine.validate_current_state(contract)
# {"is_valid": True, "state": "DRAFT", "issues": []}
```

### What `transition()` does internally

1. Resolves the current `StateHandler` from `STATE_HANDLERS`.
2. Checks `target_state` is in `handler.get_allowed_transitions()`.
3. Calls `on_exit()` on the current handler.
4. Calls `on_enter()` on the target handler (may initialise / clean up modules).
5. Updates `contract.workflow_state`, `state_changed_at`, `state_changed_by`,
   and `workflow_metadata`.
6. Persists the contract via `await contract.save()`.
7. Writes a `WorkflowHistory` document.
8. Dispatches a `STATE_CHANGED` event.

---

## Approval Workflow

### Creating a request

```python
from backend.workflows import ApprovalSystem, ApprovalType

result = await ApprovalSystem.create_approval_request(
    contract=contract,
    approval_type=ApprovalType.CONTRACT_ACTIVATION,
    requested_by=submitter_uid,
    required_approvers=[manager_uid, director_uid],
)
```

### Approving

```python
result = await ApprovalSystem.approve(
    contract=contract,
    approval_type=ApprovalType.CONTRACT_ACTIVATION,
    approver_id=manager_uid,
    comment="Looks good",
)
# When the last approver approves, the contract is automatically
# transitioned to ACTIVE.
```

### Rejecting

```python
result = await ApprovalSystem.reject(
    contract=contract,
    approval_type=ApprovalType.CONTRACT_ACTIVATION,
    rejector_id=director_uid,
    reason="Budget exceeds limit — revise and resubmit",
)
```

### ApprovalType values

| Value                  | Use case                                       |
|------------------------|------------------------------------------------|
| `contract_activation`  | Activating a contract (PENDING → ACTIVE)       |
| `budget_change`        | Modifying contract value after activation      |
| `module_change`        | Enabling or disabling modules mid-contract     |
| `contract_completion`  | Formally completing a contract                 |

---

## Event System

### Dispatching events

```python
from backend.workflows import EventDispatcher, WorkflowEventType

await EventDispatcher.dispatch(
    event_type=WorkflowEventType.STATE_CHANGED,
    payload={"contract_id": 7, "to_state": "ACTIVE"},
)
```

### Registering handlers

```python
async def notify_team(event_type, payload):
    # send a Slack message, email, etc.
    ...

EventDispatcher.register_handler(WorkflowEventType.STATE_CHANGED, notify_team)

# Wildcard — receive every event
EventDispatcher.register_handler(None, notify_team)
```

### Unregistering handlers

```python
EventDispatcher.unregister_handler(WorkflowEventType.STATE_CHANGED, notify_team)
```

### WorkflowEventType values

| Event type           | Fired when                                          |
|----------------------|-----------------------------------------------------|
| `STATE_CHANGED`      | Any successful contract state transition            |
| `APPROVAL_REQUESTED` | A new approval request is created                   |
| `APPROVAL_APPROVED`  | An approver records an approval                     |
| `APPROVAL_REJECTED`  | An approver rejects                                 |
| `MODULE_INITIALIZED` | A module is initialised (future use)                |
| `MODULE_FAILED`      | Module initialisation fails (future use)            |
| `VALIDATION_FAILED`  | Validation check fails (future use)                 |

---

## Audit Trail

### Querying WorkflowHistory

```python
from backend.models.workflow_history import WorkflowHistory

# All transitions for a contract
history = await WorkflowHistory.find(
    WorkflowHistory.contract_id == contract.uid
).sort("timestamp").to_list()

for h in history:
    print(f"{h.timestamp}: {h.from_state} → {h.to_state} by {h.changed_by}")
```

### Querying WorkflowEvent

```python
from backend.models.workflow_history import WorkflowEvent

events = await WorkflowEvent.find(
    WorkflowEvent.event_type == "STATE_CHANGED"
).sort("-timestamp").limit(50).to_list()
```

### Querying ApprovalRequest

```python
from backend.models.workflow_history import ApprovalRequest

pending = await ApprovalRequest.find(
    ApprovalRequest.contract_id == contract.uid,
    ApprovalRequest.status == "PENDING",
).to_list()
```

---

## Integration with Phase 5C Modules

### Module lifecycle

| Contract state | Module action         |
|----------------|-----------------------|
| → ACTIVE       | `module.initialize()` called for every `enabled_module` |
| → COMPLETED    | `module.cleanup()` called for every `enabled_module`    |
| → CANCELLED    | `module.cleanup()` called for every `enabled_module`    |

### Example: full activation flow

```python
from backend.models.projects import Contract
from backend.workflows import WorkflowEngine, ContractState, ApprovalSystem, ApprovalType

# 1. Load contract (state = DRAFT)
contract = await Contract.find_one(Contract.uid == 42)

# 2. Submit for approval
await WorkflowEngine.transition(contract, ContractState.PENDING_APPROVAL, changed_by=1)

# 3. Create an approval request
await ApprovalSystem.create_approval_request(
    contract=contract,
    approval_type=ApprovalType.CONTRACT_ACTIVATION,
    requested_by=1,
    required_approvers=[10],
)

# 4. Manager approves → contract auto-transitions to ACTIVE → modules initialized
await ApprovalSystem.approve(
    contract=contract,
    approval_type=ApprovalType.CONTRACT_ACTIVATION,
    approver_id=10,
)
```

---

## Database Collections

| Collection          | Document class    | Purpose                              |
|---------------------|-------------------|--------------------------------------|
| `workflow_history`  | `WorkflowHistory` | Immutable state transition log       |
| `approval_requests` | `ApprovalRequest` | Active and historical approval flows |
| `workflow_events`   | `WorkflowEvent`   | Append-only event audit log          |

---

## Contract Model Fields Added (Phase 5D)

```python
# backend/models/projects.py — Contract
workflow_state: str = "DRAFT"
workflow_metadata: Dict[str, Any] = {}
state_changed_at: Optional[datetime] = None
state_changed_by: Optional[int] = None
```

---

## Expected Outcomes

| # | Outcome |
|---|---------|
| 1 | 6-state workflow with transition validation |
| 2 | Terminal states (COMPLETED, CANCELLED) have no outgoing transitions |
| 3 | Multi-level approval system |
| 4 | Event dispatcher with handler registration / wildcard support |
| 5 | Complete audit trail via WorkflowHistory and WorkflowEvent |
| 6 | Automated module lifecycle (initialize on ACTIVE, cleanup on terminal) |
| 7 | Comprehensive test coverage without a live MongoDB connection |
| 8 | Full documentation |

---

## Future Phases

- **Phase 5E** — Contract scheduling and automated renewal reminders built on
  the WorkflowEngine transition API.
- **Webhooks** — `EventDispatcher` already has a placeholder for webhook
  delivery; implement by filling in `_deliver_webhooks()`.
