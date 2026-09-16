from datetime import UTC, datetime, timedelta

import pytest

from eis.adapters.memory.local import LocalMemoryRepository
from eis.knowledge.models import KnowledgeSource, Provenance
from eis.memory import MemoryKind, MemoryRecord, MemoryScope, MemoryStatus


def make_memory(
    content: str = "deployment uses Python 3.11",
    *,
    kind: MemoryKind = MemoryKind.FACT,
    confidence: float = 0.8,
    relevance: float = 0.9,
    observed_at: datetime | None = None,
) -> MemoryRecord:
    source = KnowledgeSource.create("event", "session/1")
    return MemoryRecord.create(
        MemoryScope.PROJECT,
        kind,
        content,
        Provenance.capture(source),
        confidence=confidence,
        relevance=relevance,
        observed_at=observed_at,
    )


def test_memory_preserves_type_provenance_and_metadata() -> None:
    memory = MemoryRecord.create(
        MemoryScope.DECISION,
        MemoryKind.DECISION,
        "Use provider-neutral interfaces",
        Provenance.capture(KnowledgeSource.create("decision-log", "decision/1")),
        confidence=0.95,
        relevance=1.0,
        metadata={"actor": "eis"},
    )
    assert memory.kind is MemoryKind.DECISION
    assert memory.scope is MemoryScope.DECISION
    assert memory.provenance.source.locator == "decision/1"
    assert memory.metadata["actor"] == "eis"


def test_confidence_and_relevance_are_bounded() -> None:
    provenance = Provenance.capture(KnowledgeSource.create("test", "memory"))
    with pytest.raises(ValueError):
        MemoryRecord.create(MemoryScope.TASK, MemoryKind.FACT, "x", provenance, confidence=1.1)
    with pytest.raises(ValueError):
        MemoryRecord.create(MemoryScope.TASK, MemoryKind.FACT, "x", provenance, relevance=-0.1)


def test_recall_prefers_relevant_active_memories() -> None:
    repo = LocalMemoryRepository()
    low = repo.store(make_memory(relevance=0.2))
    high = repo.store(make_memory("deployment uses Python 3.12", relevance=0.9))
    assert repo.recall("deployment")[0] == high
    assert repo.recall("deployment")[1] == low


def test_conflicting_memories_remain_separate() -> None:
    repo = LocalMemoryRepository()
    first = repo.store(make_memory("deployment uses Python 3.11"))
    second = repo.store(make_memory("deployment uses Python 3.12", confidence=0.6))
    matches = repo.recall("deployment uses Python")
    assert {item.id for item in matches} == {first.id, second.id}
    assert first.status is MemoryStatus.ACTIVE
    assert second.status is MemoryStatus.ACTIVE


def test_stale_memory_is_invalidated_and_hidden_by_default() -> None:
    repo = LocalMemoryRepository()
    memory = repo.store(make_memory(observed_at=datetime.now(UTC) - timedelta(days=90)))
    invalidated = repo.invalidate(memory.id, "source is obsolete")
    assert invalidated.status is MemoryStatus.INVALIDATED
    assert repo.get(memory.id) is None
    assert repo.get(memory.id, include_inactive=True) == invalidated
    assert repo.recall("deployment") == []
    assert len(repo.recall("deployment", include_inactive=True)) == 1


def test_uncertain_memory_is_retrieved_with_confidence_intact() -> None:
    repo = LocalMemoryRepository()
    repo.store(make_memory(kind=MemoryKind.UNKNOWN, confidence=0.1))
    recalled = repo.recall("deployment")[0]
    assert recalled.kind is MemoryKind.UNKNOWN
    assert recalled.confidence == 0.1


def test_superseding_does_not_delete_history() -> None:
    repo = LocalMemoryRepository()
    memory = repo.store(make_memory())
    superseded = repo.supersede(memory.id)
    assert superseded.status is MemoryStatus.SUPERSEDED
    assert repo.get(memory.id) is None
    assert repo.get(memory.id, include_inactive=True) == superseded


def test_memory_never_becomes_knowledge_implicitly() -> None:
    repo = LocalMemoryRepository()
    memory = repo.store(make_memory())
    assert repo.get(memory.id) == memory
    assert not hasattr(memory, "authority")
    assert not hasattr(repo, "promote_to_knowledge")


def test_delete_removes_memory() -> None:
    repo = LocalMemoryRepository()
    memory = repo.store(make_memory())
    repo.delete(memory.id)
    assert repo.get(memory.id, include_inactive=True) is None
