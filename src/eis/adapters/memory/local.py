"""Deterministic in-memory implementation of the memory repository."""

from __future__ import annotations

from uuid import UUID

from eis.memory.models import MemoryKind, MemoryRecord, MemoryScope, MemoryStatus


class LocalMemoryRepository:
    """Small local store for development and tests; it does not promote memory to knowledge."""

    def __init__(self) -> None:
        self._records: dict[UUID, MemoryRecord] = {}

    def store(self, memory: MemoryRecord) -> MemoryRecord:
        if memory.id in self._records:
            raise ValueError(f"memory already exists: {memory.id}")
        self._records[memory.id] = memory
        return memory

    def get(self, memory_id: UUID, *, include_inactive: bool = False) -> MemoryRecord | None:
        memory = self._records.get(memory_id)
        if memory is None or (not include_inactive and memory.status is not MemoryStatus.ACTIVE):
            return None
        return memory

    def recall(
        self,
        query: str,
        *,
        scope: MemoryScope | None = None,
        kind: MemoryKind | None = None,
        include_inactive: bool = False,
        limit: int = 20,
    ) -> list[MemoryRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")
        needle = query.casefold()
        records = []
        for memory in self._records.values():
            if scope is not None and memory.scope is not scope:
                continue
            if kind is not None and memory.kind is not kind:
                continue
            if not include_inactive and memory.status is not MemoryStatus.ACTIVE:
                continue
            if needle in str(memory.content).casefold():
                records.append(memory)
        return sorted(records, key=lambda item: (item.relevance, item.observed_at), reverse=True)[:limit]

    def update(self, memory: MemoryRecord) -> MemoryRecord:
        if memory.id not in self._records:
            raise KeyError(f"unknown memory: {memory.id}")
        self._records[memory.id] = memory
        return memory

    def invalidate(self, memory_id: UUID, reason: str) -> MemoryRecord:
        memory = self._records.get(memory_id)
        if memory is None:
            raise KeyError(f"unknown memory: {memory_id}")
        updated = memory.invalidate(reason)
        self._records[memory_id] = updated
        return updated

    def supersede(self, memory_id: UUID) -> MemoryRecord:
        memory = self._records.get(memory_id)
        if memory is None:
            raise KeyError(f"unknown memory: {memory_id}")
        updated = memory.supersede()
        self._records[memory_id] = updated
        return updated

    def delete(self, memory_id: UUID) -> None:
        self._records.pop(memory_id, None)
