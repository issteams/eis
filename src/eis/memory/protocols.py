from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from eis.memory.models import MemoryKind, MemoryRecord, MemoryScope


class MemoryRepository(Protocol):
    """Provider-neutral persistence boundary for memory."""

    def store(self, memory: MemoryRecord) -> MemoryRecord: ...

    def get(self, memory_id: UUID, *, include_inactive: bool = False) -> MemoryRecord | None: ...

    def recall(
        self,
        query: str,
        *,
        scope: MemoryScope | None = None,
        kind: MemoryKind | None = None,
        include_inactive: bool = False,
        limit: int = 20,
    ) -> Sequence[MemoryRecord]: ...

    def update(self, memory: MemoryRecord) -> MemoryRecord: ...

    def invalidate(self, memory_id: UUID, reason: str) -> MemoryRecord: ...

    def supersede(self, memory_id: UUID) -> MemoryRecord: ...

    def delete(self, memory_id: UUID) -> None: ...


class MemorySummarizer(Protocol):
    """Interface for future deterministic or model-backed memory summarization."""

    async def summarize(self, memories: Sequence[MemoryRecord]) -> str: ...


__all__ = ["MemoryRepository", "MemorySummarizer"]
