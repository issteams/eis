from __future__ import annotations

from typing import Protocol
from eis.core.protocols import Decision


class Reasoner(Protocol):
    async def assess(self, question: str, *, context: str = "") -> Decision: ...


__all__ = ["Reasoner"]
