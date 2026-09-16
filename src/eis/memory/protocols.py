from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from eis.core.protocols import Evidence


class MemoryStore(Protocol):
    async def remember(self, item: Evidence) -> None: ...
    async def recall(self, query: str, *, limit: int = 10) -> Sequence[Evidence]: ...


__all__ = ["MemoryStore"]
