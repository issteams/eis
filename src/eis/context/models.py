"""Provider-neutral models for retrieval and assembled context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class SourceKind(StrEnum):
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    PROJECT = "project"
    REPOSITORY = "repository"
    DOCUMENTATION = "documentation"
    DECISION = "decision"
    TASK = "task"


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """Identity and traceability of a retrieved item."""

    source_id: str
    source_kind: SourceKind
    locator: str
    authority: float = 1.0
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.authority <= 1:
            raise ValueError("authority must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ContextItem:
    """A ranked piece of evidence that can be assembled into model context."""

    id: UUID
    content: str
    provenance: ProvenanceRecord
    relevance: float = 0.0
    freshness: float = 1.0
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        content: str,
        provenance: ProvenanceRecord,
        *,
        relevance: float = 0.0,
        freshness: float = 1.0,
        score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ContextItem:
        return cls(uuid4(), content, provenance, relevance, freshness, score, metadata or {})


@dataclass(frozen=True, slots=True)
class Query:
    """Normalized retrieval query."""

    raw: str
    normalized: str
    terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContextRequest:
    query: str
    limit: int = 10
    max_characters: int = 12000
    source_kinds: tuple[SourceKind, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    min_score: float = 0.0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.max_characters < 1:
            raise ValueError("limit and max_characters must be positive")
        if not 0 <= self.min_score <= 1:
            raise ValueError("min_score must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ContextResult:
    query: Query
    items: tuple[ContextItem, ...]
    truncated: bool = False

    @property
    def character_count(self) -> int:
        return sum(len(item.content) for item in self.items)
