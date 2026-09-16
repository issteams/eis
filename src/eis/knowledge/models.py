"""Canonical, provider-neutral models for EIS organizational knowledge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class KnowledgeKind(StrEnum):
    """Categories of knowledge EIS can store."""

    COMPANY = "company"
    DIVISION = "division"
    PRODUCT = "product"
    PROJECT = "project"
    REPOSITORY = "repository"
    ARCHITECTURE = "architecture"
    ENGINEERING_STANDARD = "engineering_standard"
    BUSINESS_RULE = "business_rule"
    DECISION = "decision"
    TERMINOLOGY = "terminology"
    DOCUMENTATION = "documentation"
    WORKFLOW = "workflow"
    POLICY = "policy"
    HISTORICAL = "historical"


class KnowledgeStatus(StrEnum):
    """Lifecycle state of a knowledge record."""

    ACTIVE = "active"
    INVALIDATED = "invalidated"


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    """Origin of a knowledge record, including enough metadata for tracing."""

    source_id: UUID
    source_type: str
    locator: str
    title: str | None = None
    authority: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_type: str,
        locator: str,
        *,
        title: str | None = None,
        authority: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeSource:
        return cls(uuid4(), source_type, locator, title, authority, metadata or {})


@dataclass(frozen=True, slots=True)
class Provenance:
    """Traceability metadata for a knowledge version."""

    source: KnowledgeSource
    captured_at: datetime
    source_version: str | None = None
    content_hash: str | None = None
    ingested_by: str = "eis"

    @classmethod
    def capture(
        cls,
        source: KnowledgeSource,
        *,
        source_version: str | None = None,
        content_hash: str | None = None,
        ingested_by: str = "eis",
    ) -> Provenance:
        return cls(
            source=source,
            captured_at=datetime.now(UTC),
            source_version=source_version,
            content_hash=content_hash,
            ingested_by=ingested_by,
        )


@dataclass(frozen=True, slots=True)
class KnowledgeRelationship:
    """Directed relationship between two knowledge entities."""

    source_id: UUID
    relation: str
    target_id: UUID
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeVersion:
    """Immutable version of a knowledge entity."""

    version: int
    content: str | dict[str, Any]
    provenance: Provenance
    created_at: datetime
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    invalidated_at: datetime | None = None
    invalidation_reason: str | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeEntity:
    """Canonical knowledge entity with immutable version history."""

    id: UUID
    kind: KnowledgeKind
    name: str
    description: str | None
    current_version: int
    versions: tuple[KnowledgeVersion, ...]
    relationships: tuple[KnowledgeRelationship, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        kind: KnowledgeKind,
        name: str,
        content: str | dict[str, Any],
        provenance: Provenance,
        *,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        relationships: tuple[KnowledgeRelationship, ...] = (),
    ) -> KnowledgeEntity:
        now = datetime.now(UTC)
        version = KnowledgeVersion(1, content, provenance, now)
        return cls(uuid4(), kind, name, description, 1, (version,), relationships, metadata or {})

    @property
    def active_version(self) -> KnowledgeVersion | None:
        """Return the current version only when it remains authoritative."""
        version = self.versions[self.current_version - 1]
        return version if version.status is KnowledgeStatus.ACTIVE else None

    @property
    def content(self) -> str | dict[str, Any] | None:
        """Return active content; invalidated knowledge is never silently returned."""
        version = self.active_version
        return version.content if version else None

    def with_version(
        self,
        content: str | dict[str, Any],
        provenance: Provenance,
    ) -> KnowledgeEntity:
        """Create a new authoritative version while retaining historical versions."""
        now = datetime.now(UTC)
        next_version = self.current_version + 1
        version = KnowledgeVersion(next_version, content, provenance, now)
        return KnowledgeEntity(
            self.id,
            self.kind,
            self.name,
            self.description,
            next_version,
            (*self.versions, version),
            self.relationships,
            self.metadata,
        )

    def invalidate(self, reason: str) -> KnowledgeEntity:
        """Invalidate the current version without deleting its historical record."""
        now = datetime.now(UTC)
        versions = list(self.versions)
        current = versions[self.current_version - 1]
        versions[self.current_version - 1] = KnowledgeVersion(
            current.version,
            current.content,
            current.provenance,
            current.created_at,
            KnowledgeStatus.INVALIDATED,
            now,
            reason,
        )
        return KnowledgeEntity(
            self.id,
            self.kind,
            self.name,
            self.description,
            self.current_version,
            tuple(versions),
            self.relationships,
            self.metadata,
        )

    def related_to(self, relationship: KnowledgeRelationship) -> KnowledgeEntity:
        """Return an entity with an additional directed relationship."""
        if relationship.source_id != self.id:
            raise ValueError("relationship source must match entity id")
        return KnowledgeEntity(
            self.id,
            self.kind,
            self.name,
            self.description,
            self.current_version,
            self.versions,
            (*self.relationships, relationship),
            self.metadata,
        )
