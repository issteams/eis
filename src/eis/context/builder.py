"""Assembly pipeline for bounded, provenance-preserving context."""

from __future__ import annotations

from eis.context.models import ContextRequest, ContextResult
from eis.context.retrieval import ContextScorer, QueryNormalizer, deduplicate
from eis.context.protocols import Retriever


class ContextBuilder:
    """Build ranked structured context without flattening evidence into a text blob."""

    def __init__(self, retrievers: tuple[Retriever, ...], *, normalizer: QueryNormalizer | None = None) -> None:
        if not retrievers:
            raise ValueError("at least one retriever is required")
        self._retrievers = retrievers
        self._normalizer = normalizer or QueryNormalizer()
        self._scorer = ContextScorer()

    async def build(self, request: ContextRequest) -> ContextResult:
        query = self._normalizer.normalize(request.query)
        retrieved: list = []
        for retriever in self._retrievers:
            retrieved.extend(
                await retriever.retrieve(query, limit=request.limit, metadata=request.metadata)
            )
        filtered = [item for item in deduplicate(retrieved) if item.score >= request.min_score]
        ranked = self._scorer.rank(filtered)
        selected = []
        used = 0
        truncated = False
        for item in ranked:
            if len(selected) >= request.limit:
                truncated = True
                break
            size = len(item.content)
            if used + size > request.max_characters:
                truncated = True
                continue
            selected.append(item)
            used += size
        return ContextResult(query, tuple(selected), truncated)
