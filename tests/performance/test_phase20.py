from __future__ import annotations

import asyncio

from eis.context.models import ContextItem, ProvenanceRecord, SourceKind
from eis.models.interfaces import GenerationRequest, ModelMetadata
from eis.performance.cache import AsyncResponseCache
from eis.performance.context import ContextBudget, optimize_context
from eis.performance.execution import batch_gather, retry_optimized
from eis.performance.routing import ModelRoute, ModelRouter, RoutingPolicy
from eis.performance.scheduler import Priority, TaskScheduler


class FakeModel:
    metadata = ModelMetadata("test", "fast", context_window=4096)


def test_cache_single_flight() -> None:
    async def scenario() -> None:
        cache: AsyncResponseCache[str] = AsyncResponseCache(max_entries=4, ttl_seconds=10)
        calls = 0

        async def factory() -> str:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return "value"

        values = await asyncio.gather(
            *(cache.get_or_set("same", factory) for _ in range(8))
        )
        assert values == ["value"] * 8
        assert calls == 1
        assert cache.stats().misses == 8
        assert cache.stats().stores == 1
        assert await cache.get("same") == "value"
        assert cache.stats().hits == 1

    asyncio.run(scenario())


def test_context_budget_keeps_high_score_evidence() -> None:
    provenance = ProvenanceRecord(
        "source", SourceKind.KNOWLEDGE, "knowledge://1", authority=1.0
    )
    items = [ContextItem.create("high " + "x" * 100, provenance, relevance=1.0)] + [
        ContextItem.create(f"low-{i} " + "x" * 100, provenance, relevance=0.1)
        for i in range(20)
    ]
    result = optimize_context(
        items,
        ContextBudget(max_items=2, max_characters=500, reserve_characters=50),
    )
    assert result[0].content.startswith("high")
    assert len(result) <= 2
    assert result[0].provenance.source_id == "source"


def test_router_respects_task_policy() -> None:
    fast = FakeModel()
    slow = FakeModel()
    slow.metadata = ModelMetadata("test", "slow", context_window=8192)
    router = ModelRouter(
        [ModelRoute("fast", fast), ModelRoute("slow", slow)],
        RoutingPolicy(default_route="fast", task_routes={"verification": "slow"}),
    )

    selected, request = router.prepare(
        GenerationRequest(prompt="x", metadata={"task_type": "verification"})
    )
    assert selected.name == "slow"
    assert request.model == "slow"


def test_scheduler_prioritizes_and_bounds_workers() -> None:
    async def scenario() -> None:
        scheduler = TaskScheduler(workers=2, max_queue=8)
        order: list[int] = []

        async def work(value: int) -> int:
            order.append(value)
            return value

        await asyncio.gather(
            scheduler.submit(work(2), priority=Priority.BACKGROUND),
            scheduler.submit(work(1), priority=Priority.CRITICAL),
        )
        await scheduler.close()
        assert 1 in order and 2 in order

    asyncio.run(scenario())


def test_retry_only_retries_transient_failures() -> None:
    async def scenario() -> None:
        attempts = 0

        async def operation() -> int:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise TimeoutError("transient")
            return 42

        result = await retry_optimized(
            operation,
            retryable=lambda exc: isinstance(exc, TimeoutError),
        )
        assert result == 42
        assert attempts == 3

    asyncio.run(scenario())


def test_batch_gather_limits_burst_size() -> None:
    async def scenario() -> None:
        active = 0
        peak = 0

        async def operation() -> int:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1
            return 1

        result = await batch_gather([operation for _ in range(10)], batch_size=3)
        assert result == [1] * 10
        assert peak <= 3

    asyncio.run(scenario())
