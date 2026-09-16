import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from eis.context import (
    ContextBuilder,
    ContextItem,
    ContextRequest,
    InMemoryRetriever,
    ProvenanceRecord,
    Query,
    SourceKind,
)
from eis.context.retrieval import ContextScorer, KeywordRetriever, QueryNormalizer, deduplicate, freshness


def item(
    content: str,
    kind: SourceKind,
    *,
    authority: float = 1.0,
    metadata=None,
    age_days: int = 0,
) -> ContextItem:
    provenance = ProvenanceRecord(
        source_id=f"{kind}-{content}",
        source_kind=kind,
        locator=f"{kind.value}://source",
        authority=authority,
        captured_at=datetime.now(UTC) - timedelta(days=age_days),
        metadata=metadata or {},
    )
    return ContextItem.create(content, provenance, freshness=freshness(age_days * 86400, 86400))


def test_query_normalization_removes_noise_and_deduplicates_terms() -> None:
    query = QueryNormalizer().normalize("  EIS   Retrieval and EIS  ")
    assert query.normalized == "eis retrieval and eis"
    assert query.terms == ("eis", "retrieval")


def test_keyword_relevance_prefers_matching_content() -> None:
    retriever = KeywordRetriever()
    query = Query("architecture retrieval", "architecture retrieval", ("architecture", "retrieval"))
    relevant = retriever.retrieve(
        query,
        [
            item("EIS architecture and retrieval", SourceKind.KNOWLEDGE),
            item("billing only", SourceKind.MEMORY),
        ],
    )
    assert relevant[0].content == "EIS architecture and retrieval"
    assert relevant[0].relevance == 1.0


def test_metadata_filtering() -> None:
    async def run() -> None:
        retriever = InMemoryRetriever(
            [
                item("project alpha", SourceKind.PROJECT, metadata={"project": "alpha"}),
                item("project beta", SourceKind.PROJECT, metadata={"project": "beta"}),
            ]
        )
        query = QueryNormalizer().normalize("project")
        result = await retriever.retrieve(query, metadata={"project": "alpha"})
        assert [entry.content for entry in result] == ["project alpha"]

    asyncio.run(run())


def test_source_priority_and_authority_affect_ranking() -> None:
    scorer = ContextScorer()
    memory = item("same answer", SourceKind.MEMORY, authority=0.4)
    knowledge = item("same answer authoritative", SourceKind.KNOWLEDGE, authority=1.0)
    ranked = scorer.rank([memory, knowledge])
    assert ranked[0].provenance.source_kind is SourceKind.KNOWLEDGE


def test_conflicting_sources_preserve_both_provenances() -> None:
    first = item("the timeout is 30 seconds", SourceKind.MEMORY, authority=0.4)
    second = item("the timeout is 60 seconds", SourceKind.DOCUMENTATION, authority=1.0)
    result = deduplicate([first, second])
    assert len(result) == 2
    assert {entry.provenance.source_kind for entry in result} == {
        SourceKind.MEMORY,
        SourceKind.DOCUMENTATION,
    }


def test_stale_source_scores_below_fresh_source() -> None:
    fresh = item("current configuration", SourceKind.KNOWLEDGE, age_days=0)
    stale = item("old configuration", SourceKind.KNOWLEDGE, age_days=30)
    ranked = ContextScorer().rank([stale, fresh])
    assert ranked[0].content == "current configuration"


def test_context_builder_deduplicates_and_respects_character_limit() -> None:
    async def run() -> None:
        repeated = item("important repository context", SourceKind.REPOSITORY)
        memory = item("important repository context", SourceKind.MEMORY, authority=0.3)
        second = item("additional context", SourceKind.DOCUMENTATION)
        retriever = InMemoryRetriever([repeated, memory, second])
        builder = ContextBuilder((retriever,))
        result = await builder.build(
            ContextRequest("repository context", limit=10, max_characters=30)
        )
        assert len(result.items) == 1
        assert result.items[0].provenance.source_kind is SourceKind.REPOSITORY
        assert result.truncated is True
        assert result.character_count <= 30

    asyncio.run(run())


def test_provenance_is_retained_on_retrieved_items() -> None:
    source = item("authoritative fact", SourceKind.DECISION, authority=1.0)
    assert source.provenance.source_id == "decision-authoritative fact"
    assert source.provenance.locator == "decision://source"
    assert source.provenance.authority == 1.0
