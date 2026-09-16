from __future__ import annotations
from typing import Protocol, Any


class Orchestrator(Protocol):
    async def dispatch(self, task: str, *, context: dict[str, Any] | None = None) -> Any: ...


__all__ = ["Orchestrator"]
