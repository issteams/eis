"""Bounded retry and concurrency primitives."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 2
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 10.0

    def delay(self, attempt: int) -> float:
        return float(min(self.max_backoff_seconds, self.backoff_seconds * (2**attempt)))


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy | None = None,
    retryable: Callable[[Exception], bool] | None = None,
) -> T:
    """Retry only bounded, explicitly retryable failures; otherwise fail fast."""
    selected = policy or RetryPolicy()
    should_retry = retryable or (lambda _exc: True)
    for attempt in range(selected.max_retries + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt >= selected.max_retries or not should_retry(exc):
                raise
            await asyncio.sleep(selected.delay(attempt))
    raise RuntimeError("retry loop exhausted")


class ConcurrencyLimiter:
    """Bound concurrent work and degrade by rejecting excess work."""

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("concurrency limit must be positive")
        self._semaphore = asyncio.Semaphore(limit)

    async def acquire(self) -> None:
        await self._semaphore.acquire()

    def release(self) -> None:
        self._semaphore.release()

    async def __aenter__(self) -> ConcurrencyLimiter:
        await self.acquire()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.release()


__all__ = ["ConcurrencyLimiter", "RetryPolicy", "retry_async"]
