"""Bounded priority scheduling for EIS work.

High-integrity verification work can be prioritized without bypassing it. Queue bounds
provide backpressure instead of unbounded memory growth.
"""

from __future__ import annotations

import asyncio
import itertools
from enum import IntEnum
from typing import Any, Awaitable, TypeVar

T = TypeVar("T")


class Priority(IntEnum):
    BACKGROUND = 30
    NORMAL = 20
    HIGH = 10
    CRITICAL = 0


class TaskScheduler:
    """Async priority queue with bounded workers and queue depth."""

    def __init__(self, *, workers: int = 4, max_queue: int = 128) -> None:
        if workers < 1 or max_queue < 1:
            raise ValueError("workers and max_queue must be positive")
        self._queue: asyncio.PriorityQueue[tuple[int, int, Awaitable[Any], asyncio.Future[Any]]] = (
            asyncio.PriorityQueue(maxsize=max_queue)
        )
        self._workers = workers
        self._sequence = itertools.count()
        self._tasks: list[asyncio.Task[None]] = []
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._tasks = [asyncio.create_task(self._worker()) for _ in range(self._workers)]

    async def submit(self, operation: Awaitable[T], *, priority: Priority = Priority.NORMAL) -> T:
        if not self._started:
            await self.start()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[T] = loop.create_future()
        await self._queue.put((int(priority), next(self._sequence), operation, future))
        return await future

    async def _worker(self) -> None:
        while True:
            _, _, operation, future = await self._queue.get()
            try:
                if future.cancelled():
                    continue
                result = await operation
                future.set_result(result)
            except asyncio.CancelledError:
                if not future.done():
                    future.cancel()
                raise
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)
            finally:
                self._queue.task_done()

    async def drain(self) -> None:
        await self._queue.join()

    async def close(self) -> None:
        if not self._started:
            return
        await self.drain()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._started = False

    @property
    def queued(self) -> int:
        return self._queue.qsize()
