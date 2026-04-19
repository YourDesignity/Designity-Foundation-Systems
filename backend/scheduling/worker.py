"""
Background worker for the Phase 5E scheduling system.

Run this module as a long-lived asyncio task alongside your FastAPI server to
continuously process due scheduled jobs.

Usage (from main.py lifespan or a standalone script):

    from backend.scheduling.worker import SchedulingWorker

    worker = SchedulingWorker(interval_seconds=60)
    asyncio.create_task(worker.start())
"""

from __future__ import annotations

import asyncio

from backend.scheduling.engine import SchedulingEngine


class SchedulingWorker:
    """
    Background worker that continuously polls for and processes due jobs.

    The worker runs in an asyncio event loop, calling
    :meth:`SchedulingEngine.process_due_jobs` on every tick.  Any unhandled
    exception from the engine is caught and logged so the worker never silently
    dies.

    Parameters
    ----------
    interval_seconds:
        How many seconds to wait between polling cycles (default: 60).
    """

    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds = interval_seconds
        self.running = False

    async def start(self) -> None:
        """Start the worker loop.  Runs indefinitely until :meth:`stop` is called."""
        self.running = True
        while self.running:
            try:
                summary = await SchedulingEngine.process_due_jobs()
                if summary.get("executed", 0) > 0:
                    print(
                        f"[SchedulingWorker] Processed {summary['executed']} job(s) — "
                        f"succeeded={summary['succeeded']} failed={summary['failed']} "
                        f"retried={summary.get('retried', 0)}"
                    )
            except Exception as exc:  # noqa: BLE001
                # Log error but keep the worker alive
                print(f"[SchedulingWorker] Error during job processing: {exc}")

            await asyncio.sleep(self.interval_seconds)

    def stop(self) -> None:
        """Signal the worker loop to stop after the current sleep completes."""
        self.running = False
