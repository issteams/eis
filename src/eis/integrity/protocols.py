from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from eis.core.protocols import Evidence


class IntegrityChecker(Protocol):
    def check(self, claim: str, evidence: Sequence[Evidence]) -> bool: ...


class ProvenanceTracker(Protocol):
    def record(self, evidence: Evidence) -> None: ...


__all__ = ["IntegrityChecker", "ProvenanceTracker"]
