from __future__ import annotations

from typing import Protocol, Sequence
from eis.core.protocols import Evidence


class MemoryStore(Protocol):
    async def remember(self, item: Evidence) -> None: ...
    async def recall(self, query: str, *, limit: int = 10) -> Sequence[Evidence]: ...


__all__ = ["MemoryStore"]
