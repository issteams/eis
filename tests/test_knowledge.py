from datetime import datetime, timezone

import pytest

from eis.adapters.knowledge.local import LocalKnowledgeRepository
from eis.knowledge import KnowledgeEntity, KnowledgeKind, KnowledgeRelationship, KnowledgeSource, KnowledgeStatus, Provenance


def make_entity(name: str = "Architecture") -> KnowledgeEntity:
    source = KnowledgeSource.create("document", "docs/architecture.md", authority="echowavs")
    return KnowledgeEntity.create(
        KnowledgeKind.ARCHITECTURE,
        name,
        {"layers": ["core", "adapters"]},
        Provenance.capture(source, source_version="abc123", content_hash="hash"),
    )


def test_create_and_retrieve() -> None:
    repo = LocalKnowledgeRepository()
    entity = make_entity()
    assert repo.create(entity) == entity
    assert repo.get(entity.id) == entity


def test_structured_content_and_provenance_are_retained() -> None:
    entity = make_entity()
    assert entity.content == {"layers": ["core", "adapters"]}
    assert entity.active_version is not None
    assert entity.active_version.provenance.source.locator == "docs/architecture.md"
    assert entity.active_version.provenance.source_version == "abc123"
    assert entity.active_version.created_at.tzinfo == timezone.utc


def test_relationships_are_explicit() -> None:
    repo = LocalKnowledgeRepository()
    parent = repo.create(make_entity("Project"))
    child = repo.create(make_entity("Repository"))
    relation = KnowledgeRelationship(parent.id, "contains", child.id)
    updated = repo.add_relationship(relation)
    assert updated.relationships == (relation,)
    assert repo.get(child.id) == child


def test_updates_create_new_version_and_preserve_history() -> None:
    repo = LocalKnowledgeRepository()
    entity = repo.create(make_entity())
    source = KnowledgeSource.create("git", "repo@def456", authority="echowavs")
    updated = entity.with_version("updated architecture", Provenance.capture(source, source_version="def456"))
    repo.update(updated)
    stored = repo.get(entity.id)
    assert stored is not None
    assert stored.current_version == 2
    assert len(stored.versions) == 2
    assert stored.content == "updated architecture"
    assert stored.versions[0].provenance.source.locator == "docs/architecture.md"


def test_invalidation_never_returns_stale_knowledge_as_active() -> None:
    repo = LocalKnowledgeRepository()
    entity = repo.create(make_entity())
    invalidated = repo.invalidate(entity.id, "source superseded")
    assert invalidated.active_version is None
    assert invalidated.content is None
    assert repo.get(entity.id) is None
    assert repo.get(entity.id, include_invalidated=True) == invalidated
    assert invalidated.versions[0].status is KnowledgeStatus.INVALIDATED
    assert invalidated.versions[0].invalidation_reason == "source superseded"
    assert invalidated.versions[0].invalidated_at is not None


def test_search_filters_by_kind_and_excludes_invalidated_by_default() -> None:
    repo = LocalKnowledgeRepository()
    architecture = repo.create(make_entity("EIS Architecture"))
    repo.create(KnowledgeEntity.create(
        KnowledgeKind.POLICY,
        "Security Policy",
        "protect credentials",
        Provenance.capture(KnowledgeSource.create("policy", "security/policy.md")),
    ))
    repo.invalidate(architecture.id, "obsolete")
    assert repo.search("architecture") == []
    assert len(repo.search("policy", kind=KnowledgeKind.POLICY)) == 1
    assert repo.search("architecture", include_invalidated=True)[0].id == architecture.id


def test_delete_removes_entity() -> None:
    repo = LocalKnowledgeRepository()
    entity = repo.create(make_entity())
    repo.delete(entity.id)
    assert repo.get(entity.id) is None


def test_invalid_relationship_source_is_rejected() -> None:
    repo = LocalKnowledgeRepository()
    entity = repo.create(make_entity())
    with pytest.raises(KeyError):
        repo.add_relationship(KnowledgeRelationship(entity.id, "contains", entity.id)) if False else repo.add_relationship(
            KnowledgeRelationship(entity.id, "contains", entity.id)
        )


def test_entity_rejects_relationship_for_another_source() -> None:
    entity = make_entity()
    other = make_entity("Other")
    with pytest.raises(ValueError, match="relationship source"):
        entity.related_to(KnowledgeRelationship(other.id, "contains", entity.id))
