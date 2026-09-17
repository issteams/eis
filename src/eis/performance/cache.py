"""Correctness-preserving cache primitives.

Only explicitly cacheable successful values should be stored. Callers decide whether a
request is safe to cache; verification-sensitive or freshness-sensitive operations can
simply set cacheable=False.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class CacheStats:
    hits: int = 0
    misses: int = 0
    stores: int = 0
    evictions: int = 0


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    expires_at: float


class AsyncResponseCache(Generic[T]):
    """Small bounded TTL cache with per-key single-flight protection."""

    def __init__(self, *, max_entries: int = 512, ttl_seconds: float = 300.0) -> None:
        if max_entries < 1 or ttl_seconds <= 0:
            raise ValueError("max_entries must be positive and ttl_seconds must be positive")
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._entries: OrderedDict[str, _Entry[T]] = OrderedDict()
        self._inflight: dict[str, asyncio.Future[T]] = {}
        self._lock = asyncio.Lock()
        self._hits = self._misses = self._stores = self._evictions = 0

    @staticmethod
    def key(*parts: object) -> str:
        payload = "\x1f".join(repr(part) for part in parts).encode()
        return hashlib.sha256(payload).hexdigest()

    async def get(self, key: str) -> T | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at <= time.monotonic():
                self._entries.pop(key, None)
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return entry.value

    async def set(self, key: str, value: T, *, ttl_seconds: float | None = None) -> None:
        async with self._lock:
            self._entries[key] = _Entry(value, time.monotonic() + (ttl_seconds or self._ttl))
            self._entries.move_to_end(key)
            self._stores += 1
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
                self._evictions += 1

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        *,
        cacheable: bool = True,
    ) -> T:
        if not cacheable:
            return await factory()
        cached = await self.get(key)
        if cached is not None:
            return cached

        async with self._lock:
            future = self._inflight.get(key)
            if future is None:
                future = asyncio.get_running_loop().create_future()
                self._inflight[key] = future
                owner = True
            else:
                owner = False
        if not owner:
            return await future

        try:
            value = await factory()
            await self.set(key, value)
            future.set_result(value)
            return value
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

    def stats(self) -> CacheStats:
        return CacheStats(self._hits, self._misses, self._stores, self._evictions)
