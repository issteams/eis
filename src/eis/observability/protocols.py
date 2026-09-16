from __future__ import annotations
from typing import Protocol, Any


class AuditSink(Protocol):
    def record(self, event: str, *, data: dict[str, Any] | None = None) -> None: ...


__all__ = ["AuditSink"]
