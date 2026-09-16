from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from eis.knowledge.models import Provenance


class MemoryScope(StrEnum):
    ORGANIZATIONAL = "organizational"
    PROJECT = "project"
    TASK = "task"
    AGENT = "agent"
    SESSION = "session"
    EPISODIC = "episodic"
    DECISION = "decision"
    FAILURE = "failure"


class MemoryKind(StrEnum):
    FACT = "fact"
    OBSERVATION = "observation"
    DECISION = "decision"
    ASSUMPTION = "assumption"
    INFERENCE = "inference"
    EXPERIENCE = "experience"
    FAILURE = "failure"
    PREFERENCE = "preference"
    UNKNOWN = "unknown"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    INVALIDATED = "invalidated"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    """A provenance-aware memory item; storage never makes it authoritative knowledge."""

    id: UUID
    scope: MemoryScope
    kind: MemoryKind
    content: str | dict[str, Any]
    provenance: Provenance
    created_at: datetime
    observed_at: datetime
    confidence: float
    relevance: float
    status: MemoryStatus = MemoryStatus.ACTIVE
    invalidated_at: datetime | None = None
    invalidation_reason: str | None = None
    supersedes: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        scope: MemoryScope,
        kind: MemoryKind,
        content: str | dict[str, Any],
        provenance: Provenance,
        *,
        confidence: float = 0.5,
        relevance: float = 0.5,
        observed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        supersedes: UUID | None = None,
    ) -> MemoryRecord:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not 0.0 <= relevance <= 1.0:
            raise ValueError("relevance must be between 0 and 1")
        now = datetime.now(UTC)
        observed = observed_at or now
        if observed.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return cls(
            uuid4(), scope, kind, content, provenance, now, observed,
            confidence, relevance, metadata=metadata or {}, supersedes=supersedes,
        )

    def invalidate(self, reason: str) -> MemoryRecord:
        if not reason.strip():
            raise ValueError("invalidation reason must not be empty")
        return MemoryRecord(
            self.id, self.scope, self.kind, self.content, self.provenance,
            self.created_at, self.observed_at, self.confidence, self.relevance,
            MemoryStatus.INVALIDATED, datetime.now(UTC), reason, self.supersedes, self.metadata,
        )

    def supersede(self) -> MemoryRecord:
        return MemoryRecord(
            self.id, self.scope, self.kind, self.content, self.provenance,
            self.created_at, self.observed_at, self.confidence, self.relevance,
            MemoryStatus.SUPERSEDED, self.invalidated_at, self.invalidation_reason,
            self.supersedes, self.metadata,
        )


__all__ = ["MemoryKind", "MemoryRecord", "MemoryScope", "MemoryStatus"]
