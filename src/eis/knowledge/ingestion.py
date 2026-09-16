"""Provider-neutral ingestion contracts for future knowledge sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from eis.knowledge.models import KnowledgeEntity, KnowledgeSource


@dataclass(frozen=True, slots=True)
class KnowledgeInput:
    """Normalized source payload before it becomes canonical knowledge."""

    source: KnowledgeSource
    content: str | dict[str, Any]
    name: str
    kind: str
    description: str | None = None
    source_version: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeIngestor(Protocol):
    """Convert an external source into normalized knowledge inputs."""

    def ingest(self) -> list[KnowledgeInput]: ...


class KnowledgeSourceConnector(KnowledgeIngestor, Protocol):
    """Marker contract for connectors such as GitHub, filesystem and databases."""


class KnowledgeWriter(Protocol):
    """Persist normalized inputs as canonical entities."""

    def write(self, item: KnowledgeInput) -> KnowledgeEntity: ...
