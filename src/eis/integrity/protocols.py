from __future__ import annotations

from typing import Protocol, Sequence
from eis.core.protocols import Evidence


class IntegrityChecker(Protocol):
    def check(self, claim: str, evidence: Sequence[Evidence]) -> bool: ...


class ProvenanceTracker(Protocol):
    def record(self, evidence: Evidence) -> None: ...


__all__ = ["IntegrityChecker", "ProvenanceTracker"]
