"""Stable retrieval contracts for keyword, semantic, and hybrid backends."""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from eis.context.models import ContextItem, Query


@runtime_checkable
class Retriever(Protocol):
    async def retrieve(
        self,
        query: Query,
        *,
        limit: int = 20,
        metadata: dict[str, object] | None = None,
    ) -> list[ContextItem]: ...


@runtime_checkable
class SemanticRetriever(Retriever, Protocol):
    async def retrieve_semantic(
        self,
        query: Query,
        *,
        limit: int = 20,
        metadata: dict[str, object] | None = None,
    ) -> list[ContextItem]: ...


class QueryNormalizer(Protocol):
    def normalize(self, query: str) -> Query: ...


class Ranker(Protocol):
    def rank(self, query: Query, items: Sequence[ContextItem]) -> list[ContextItem]: ...
