"""Reference worker loop for persistent EIS jobs."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from eis.observability.jobs import GracefulShutdown, Job, JobStore
from eis.observability.models import TaskMetric
from eis.observability.runtime import Observability


class Worker:
    """Process durable jobs with bounded attempts and graceful shutdown."""

    def __init__(
        self,
        store: JobStore,
        handlers: dict[str, Callable[[Job], Awaitable[None]]],
        *,
        observability: Observability | None = None,
        lease_seconds: int = 300,
        max_attempts: int = 3,
    ) -> None:
        self.store = store
        self.handlers = handlers
        self.observability = observability or Observability()
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self.shutdown = GracefulShutdown()

    async def run_once(self) -> bool:
        if not self.shutdown.should_accept():
            return False
        self.store.recover_expired()
        job = self.store.claim(self.lease_seconds)
        if job is None:
            return False
        handler = self.handlers.get(job.kind)
        if handler is None:
            self.store.fail(job.id, f"no handler for job kind: {job.kind}", retry=False)
            return True
        started = asyncio.get_running_loop().time()
        try:
            await handler(job)
        except Exception as exc:
            retry = job.attempts < self.max_attempts
            self.store.fail(job.id, str(exc), retry=retry)
            self.observability.record_task(
                TaskMetric(
                    job.kind,
                    "retry" if retry else "failed",
                    asyncio.get_running_loop().time() - started,
                    job.attempts,
                )
            )
        else:
            self.store.complete(job.id)
            self.observability.record_task(
                TaskMetric(
                    job.kind,
                    "completed",
                    asyncio.get_running_loop().time() - started,
                    job.attempts - 1,
                )
            )
        return True

    def stop(self) -> None:
        self.shutdown.begin()


__all__ = ["Worker"]
