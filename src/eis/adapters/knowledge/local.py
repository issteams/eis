"""In-memory development implementation of the knowledge repository."""

from __future__ import annotations

from uuid import UUID

from eis.knowledge.models import KnowledgeEntity, KnowledgeKind, KnowledgeRelationship


class LocalKnowledgeRepository:
    """Small deterministic local store for development and unit tests."""

    def __init__(self) -> None:
        self._entities: dict[UUID, KnowledgeEntity] = {}

    def create(self, entity: KnowledgeEntity) -> KnowledgeEntity:
        if entity.id in self._entities:
            raise ValueError(f"knowledge entity already exists: {entity.id}")
        self._entities[entity.id] = entity
        return entity

    def get(self, entity_id: UUID, *, include_invalidated: bool = False) -> KnowledgeEntity | None:
        entity = self._entities.get(entity_id)
        if entity is None:
            return None
        if not include_invalidated and entity.active_version is None:
            return None
        return entity

    def search(
        self,
        query: str,
        *,
        kind: KnowledgeKind | None = None,
        include_invalidated: bool = False,
        limit: int = 20,
    ) -> list[KnowledgeEntity]:
        if limit < 1:
            raise ValueError("limit must be positive")
        needle = query.casefold()
        matches = []
        for entity in self._entities.values():
            if kind is not None and entity.kind is not kind:
                continue
            if not include_invalidated and entity.active_version is None:
                continue
            haystack = f"{entity.name} {entity.description or ''} {entity.content or ''}".casefold()
            if needle in haystack:
                matches.append(entity)
        return matches[:limit]

    def update(self, entity: KnowledgeEntity) -> KnowledgeEntity:
        if entity.id not in self._entities:
            raise KeyError(f"unknown knowledge entity: {entity.id}")
        self._entities[entity.id] = entity
        return entity

    def add_relationship(self, relationship: KnowledgeRelationship) -> KnowledgeEntity:
        entity = self._entities.get(relationship.source_id)
        if entity is None:
            raise KeyError(f"unknown knowledge entity: {relationship.source_id}")
        updated = entity.related_to(relationship)
        self._entities[entity.id] = updated
        return updated

    def invalidate(self, entity_id: UUID, reason: str) -> KnowledgeEntity:
        entity = self._entities.get(entity_id)
        if entity is None:
            raise KeyError(f"unknown knowledge entity: {entity_id}")
        updated = entity.invalidate(reason)
        self._entities[entity_id] = updated
        return updated

    def delete(self, entity_id: UUID) -> None:
        self._entities.pop(entity_id, None)
