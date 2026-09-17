"""Execution optimizations that keep failures explicit."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 8.0
    jitter: float = 0.1

    def __post_init__(self) -> None:
        if (
            self.max_attempts < 1
            or self.base_delay_seconds < 0
            or self.max_delay_seconds < 0
        ):
            raise ValueError("invalid retry configuration")


async def retry_optimized(
    operation: Callable[[], Awaitable[T]],
    *,
    retryable: Callable[[Exception], bool],
    config: RetryConfig | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Retry only known-transient failures with capped exponential backoff and jitter."""
    selected = config or RetryConfig()
    for attempt in range(selected.max_attempts):
        try:
            return await operation()
        except Exception as exc:
            if attempt + 1 >= selected.max_attempts or not retryable(exc):
                raise
            delay = min(
                selected.max_delay_seconds,
                selected.base_delay_seconds * (2**attempt),
            )
            if selected.jitter:
                delay += random.uniform(0.0, delay * selected.jitter)
            await sleep(delay)
    raise RuntimeError("retry loop exhausted")


async def batch_gather(
    operations: Sequence[Callable[[], Awaitable[T]]], *, batch_size: int = 16
) -> list[T]:
    """Execute independent operations in bounded batches to avoid burst amplification."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    results: list[T] = []
    for start in range(0, len(operations), batch_size):
        batch = operations[start : start + batch_size]
        results.extend(await asyncio.gather(*(operation() for operation in batch)))
    return results
