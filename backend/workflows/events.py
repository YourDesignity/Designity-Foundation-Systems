"""Event dispatcher for the Phase 5D workflow engine."""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class WorkflowEventType(str, Enum):
    STATE_CHANGED = "STATE_CHANGED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_APPROVED = "APPROVAL_APPROVED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    MODULE_INITIALIZED = "MODULE_INITIALIZED"
    MODULE_FAILED = "MODULE_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


# Type alias for an async event handler callable
EventHandlerFn = Callable[[WorkflowEventType, Dict[str, Any]], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# EventDispatcher
# ---------------------------------------------------------------------------


class EventDispatcher:
    """
    Central event bus for workflow events.

    Handlers can be registered per event type or as wildcard listeners
    (``event_type=None``).  Each ``dispatch`` call runs all matching handlers
    concurrently via ``asyncio.gather``.

    Example::

        async def my_handler(event_type, payload):
            print(event_type, payload)

        EventDispatcher.register_handler(WorkflowEventType.STATE_CHANGED, my_handler)
        await EventDispatcher.dispatch(WorkflowEventType.STATE_CHANGED, {"contract_id": 1})
    """

    # {event_type: [handler, ...]}  — None key = wildcard
    _handlers: Dict[Optional[WorkflowEventType], List[EventHandlerFn]] = {}

    @classmethod
    def register_handler(
        cls,
        event_type: Optional[WorkflowEventType],
        handler: EventHandlerFn,
    ) -> None:
        """
        Register *handler* for *event_type*.

        Pass ``event_type=None`` to receive every event (wildcard listener).
        """
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        if handler not in cls._handlers[event_type]:
            cls._handlers[event_type].append(handler)

    @classmethod
    def unregister_handler(
        cls,
        event_type: Optional[WorkflowEventType],
        handler: EventHandlerFn,
    ) -> None:
        """Remove *handler* from the *event_type* bucket (if present)."""
        bucket = cls._handlers.get(event_type, [])
        if handler in bucket:
            bucket.remove(handler)

    @classmethod
    async def dispatch(
        cls,
        event_type: WorkflowEventType,
        payload: Dict[str, Any],
    ) -> None:
        """
        Send *event_type* / *payload* to all registered handlers and log the
        event to the ``WorkflowEvent`` collection.

        Handlers are executed concurrently; individual handler errors are
        silently swallowed so one bad handler cannot block the others.
        """
        # Collect specific + wildcard handlers
        handlers: List[EventHandlerFn] = []
        handlers.extend(cls._handlers.get(event_type, []))
        handlers.extend(cls._handlers.get(None, []))  # wildcard

        if handlers:
            async def _safe(h: EventHandlerFn) -> None:
                try:
                    await h(event_type, payload)
                except Exception:  # noqa: BLE001
                    pass

            await asyncio.gather(*(_safe(h) for h in handlers))

        # Persist event log (best-effort)
        await cls._log_event(event_type, payload)

        # Placeholder: webhook delivery would go here
        # await cls._deliver_webhooks(event_type, payload)

    @classmethod
    async def _log_event(
        cls,
        event_type: WorkflowEventType,
        payload: Dict[str, Any],
    ) -> None:
        """Persist a WorkflowEvent document (best-effort; never raises)."""
        try:
            from backend.models.workflow_history import WorkflowEvent

            event = WorkflowEvent(
                event_type=event_type.value,
                payload=payload,
                timestamp=datetime.now(),
            )
            await event.insert()
        except Exception:  # noqa: BLE001
            pass
