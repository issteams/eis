"""Stable repository contract for canonical EIS knowledge."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from eis.knowledge.models import KnowledgeEntity, KnowledgeKind, KnowledgeRelationship


class KnowledgeRepository(Protocol):
    """Storage abstraction independent of any database or search engine."""

    def create(self, entity: KnowledgeEntity) -> KnowledgeEntity: ...

    def get(
        self,
        entity_id: UUID,
        *,
        include_invalidated: bool = False,
    ) -> KnowledgeEntity | None: ...

    def search(
        self,
        query: str,
        *,
        kind: KnowledgeKind | None = None,
        include_invalidated: bool = False,
        limit: int = 20,
    ) -> list[KnowledgeEntity]: ...

    def update(self, entity: KnowledgeEntity) -> KnowledgeEntity: ...

    def add_relationship(
        self,
        relationship: KnowledgeRelationship,
    ) -> KnowledgeEntity: ...

    def invalidate(self, entity_id: UUID, reason: str) -> KnowledgeEntity: ...

    def delete(self, entity_id: UUID) -> None: ...
