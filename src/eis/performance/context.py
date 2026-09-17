"""Context compaction that reduces tokens without weakening provenance semantics."""

from __future__ import annotations

from dataclasses import dataclass

from eis.context.models import ContextItem
from eis.context.retrieval import ContextScorer, deduplicate


@dataclass(frozen=True, slots=True)
class ContextBudget:
    max_items: int = 12
    max_characters: int = 24000
    reserve_characters: int = 2000

    def __post_init__(self) -> None:
        if self.max_items < 1 or self.max_characters <= self.reserve_characters:
            raise ValueError("invalid context budget")


def optimize_context(items: list[ContextItem], budget: ContextBudget | None = None) -> list[ContextItem]:
    """Deduplicate and rank evidence, then fit it into a deterministic character budget.

    Items are never rewritten, provenance is retained, and selection is score-first. This
    is a transport optimization only; verification code must still validate the selected
    evidence before making claims.
    """
    selected_budget = budget or ContextBudget()
    ranked = ContextScorer().rank(deduplicate(items))
    output: list[ContextItem] = []
    used = 0
    limit = selected_budget.max_characters - selected_budget.reserve_characters
    for item in ranked:
        if len(output) >= selected_budget.max_items:
            break
        size = len(item.content)
        if used + size > limit:
            continue
        output.append(item)
        used += size
    return output


def approximate_tokens(items: list[ContextItem]) -> int:
    """Provider-neutral token estimate for benchmarking (characters / 4)."""
    return max(0, sum(len(item.content) for item in items) // 4)
