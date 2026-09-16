"""Retrieval primitives and an in-memory backend for the context engine."""

from __future__ import annotations

import re
from collections.abc import Iterable
from math import exp

from eis.context.models import ContextItem, Query, SourceKind

_STOPWORDS = frozenset(
    [
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
        "was", "were", "with",
    ]
)


class QueryNormalizer:
    """Normalize human queries into stable lexical retrieval terms."""

    def normalize(self, query: str) -> Query:
        raw = query.strip()
        normalized = re.sub(r"\s+", " ", raw.casefold())
        terms = tuple(
            dict.fromkeys(
                term
                for term in re.findall(r"[\w-]+", normalized)
                if term not in _STOPWORDS
            )
        )
        return Query(raw=raw, normalized=normalized, terms=terms)


class KeywordRetriever:
    """Simple deterministic lexical scorer suitable for local retrieval and tests."""

    def score(self, query: Query, item: ContextItem) -> float:
        if not query.terms:
            return 0.0
        text = item.content.casefold()
        matched = sum(1 for term in query.terms if term in text)
        return matched / len(query.terms)

    def retrieve(
        self,
        query: Query,
        items: Iterable[ContextItem],
        *,
        limit: int = 20,
    ) -> list[ContextItem]:
        scored = [self._with_score(item, self.score(query, item)) for item in items]
        return sorted(
            scored,
            key=lambda item: (-item.score, -item.provenance.authority, str(item.id)),
        )[:limit]

    @staticmethod
    def _with_score(item: ContextItem, relevance: float) -> ContextItem:
        score = (
            relevance * 0.55
            + item.provenance.authority * 0.30
            + item.freshness * 0.15
        )
        return ContextItem(
            item.id,
            item.content,
            item.provenance,
            relevance,
            item.freshness,
            score,
            item.metadata,
        )


class InMemoryRetriever:
    """Composable retrieval backend with metadata filtering and lexical scoring."""

    def __init__(self, items: Iterable[ContextItem] = ()) -> None:
        self._items = list(items)
        self._keyword = KeywordRetriever()

    def add(self, item: ContextItem) -> None:
        self._items.append(item)

    async def retrieve(
        self,
        query: Query,
        *,
        limit: int = 20,
        metadata: dict[str, object] | None = None,
    ) -> list[ContextItem]:
        candidates = self._filter(self._items, metadata or {})
        return self._keyword.retrieve(query, candidates, limit=limit)

    async def retrieve_semantic(
        self,
        query: Query,
        *,
        limit: int = 20,
        metadata: dict[str, object] | None = None,
    ) -> list[ContextItem]:
        """Semantic extension point; local fallback uses lexical relevance."""
        return await self.retrieve(query, limit=limit, metadata=metadata)

    @staticmethod
    def _filter(
        items: Iterable[ContextItem],
        metadata: dict[str, object],
    ) -> list[ContextItem]:
        return [
            item
            for item in items
            if all(
                item.metadata.get(key, item.provenance.metadata.get(key)) == value
                for key, value in metadata.items()
            )
        ]


class ContextScorer:
    """Blend relevance, authority, freshness, and source priority."""

    def __init__(self) -> None:
        self.priorities = {
            SourceKind.KNOWLEDGE: 1.0,
            SourceKind.DECISION: 0.98,
            SourceKind.DOCUMENTATION: 0.92,
            SourceKind.REPOSITORY: 0.88,
            SourceKind.PROJECT: 0.82,
            SourceKind.TASK: 0.68,
            SourceKind.MEMORY: 0.55,
        }

    def score(self, item: ContextItem) -> float:
        priority = self.priorities[item.provenance.source_kind]
        return (
            item.relevance * 0.55
            + item.provenance.authority * 0.25
            + item.freshness * 0.10
            + priority * 0.10
        )

    def rank(self, items: Iterable[ContextItem]) -> list[ContextItem]:
        ranked = [
            ContextItem(
                i.id,
                i.content,
                i.provenance,
                i.relevance,
                i.freshness,
                self.score(i),
                i.metadata,
            )
            for i in items
        ]
        return sorted(
            ranked,
            key=lambda i: (-i.score, -i.provenance.authority, str(i.id)),
        )


def deduplicate(items: Iterable[ContextItem]) -> list[ContextItem]:
    """Remove repeated content while retaining the highest-authority provenance."""
    best: dict[str, ContextItem] = {}
    for item in items:
        key = item.content.strip().casefold()
        current = best.get(key)
        if current is None or (
            item.provenance.authority,
            item.score,
        ) > (
            current.provenance.authority,
            current.score,
        ):
            best[key] = item
    return list(best.values())


def freshness(captured_age_seconds: float, half_life_seconds: float) -> float:
    if captured_age_seconds <= 0:
        return 1.0
    if half_life_seconds <= 0:
        raise ValueError("half_life_seconds must be positive")
    return exp(-0.69314718056 * captured_age_seconds / half_life_seconds)
