from __future__ import annotations

import asyncio

import pytest

from eis.models.interfaces import GenerationRequest, ModelMetadata
from eis.observability.model import ModelUsageMetric
from eis.observability.performance import PerformanceRecorder
from eis.performance.cache import AsyncResponseCache
from eis.performance.context import ContextBudget, optimize_context
from eis.performance.execution import RetryConfig, batch_gather, retry_optimized
from eis.performance.profiler import PerformanceProfiler
from eis.performance.routing import ModelRoute, ModelRouter, RoutingPolicy
from eis.performance.scheduler import Priority, TaskScheduler


class FakeModel:
    metadata = ModelMetadata("test", "fast", context_window=4096)


def test_cache_eviction_and_uncacheable() -> None:
    async def scenario() -> None:
        cache: AsyncResponseCache[str] = AsyncResponseCache(max_entries=1, ttl_seconds=10)
        await cache.set("a", "one")
        await cache.set("b", "two")
        assert await cache.get("a") is None
        assert await cache.get("b") == "two"

        calls = 0

        async def factory() -> str:
            nonlocal calls
            calls += 1
            return "fresh"

        assert await cache.get_or_set("c", factory, cacheable=False) == "fresh"
        assert calls == 1
        assert await cache.get("c") is None
        await cache.clear()
        assert await cache.get("b") is None

    asyncio.run(scenario())


def test_cache_exception_propagates() -> None:
    async def scenario() -> None:
        cache: AsyncResponseCache[str] = AsyncResponseCache()

        async def factory() -> str:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await cache.get_or_set("error", factory)

    asyncio.run(scenario())


def test_context_budget_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        ContextBudget(max_items=0)
    with pytest.raises(ValueError):
        ContextBudget(max_characters=0)


def test_router_explicit_model_and_cost() -> None:
    fast = FakeModel()
    slow = FakeModel()
    slow.metadata = ModelMetadata("test", "slow", context_window=8192)
    router = ModelRouter(
        [
            ModelRoute(
                "fast",
                fast,
                price_per_million_input=1.0,
                price_per_million_output=2.0,
            ),
            ModelRoute("slow", slow),
        ],
        RoutingPolicy(default_route="fast"),
    )
    selected, request = router.prepare(GenerationRequest(prompt="x", model="slow"))
    assert selected.name == "slow"
    assert request.model == "slow"
    assert router.estimate_cost(router.route(request), 1_000_000, 2_000_000) == 0.0
    assert (
        router.estimate_cost(router.route(GenerationRequest(prompt="x")), 1_000_000, 2_000_000)
        == 5.0
    )
    assert len(router.metadata()) == 2


def test_router_rejects_unknown_routes() -> None:
    model = FakeModel()
    with pytest.raises(ValueError):
        ModelRouter([ModelRoute("fast", model)], RoutingPolicy(default_route="missing"))


def test_retry_non_retryable_failure() -> None:
    async def scenario() -> None:
        calls = 0

        async def operation() -> None:
            nonlocal calls
            calls += 1
            raise ValueError("permanent")

        with pytest.raises(ValueError, match="permanent"):
            await retry_optimized(operation, retryable=lambda exc: isinstance(exc, TimeoutError))
        assert calls == 1

    asyncio.run(scenario())


def test_retry_config_validation() -> None:
    with pytest.raises(ValueError):
        RetryConfig(max_attempts=0)
    with pytest.raises(ValueError):
        RetryConfig(base_delay_seconds=-1)


def test_batch_validation() -> None:
    async def scenario() -> None:
        with pytest.raises(ValueError):
            await batch_gather([], batch_size=0)

    asyncio.run(scenario())


def test_scheduler_close_without_start() -> None:
    async def scenario() -> None:
        scheduler = TaskScheduler()
        await scheduler.close()
        assert scheduler.queued == 0

    asyncio.run(scenario())


def test_profiler_summary() -> None:
    async def scenario() -> None:
        profiler = PerformanceProfiler()
        async with profiler.measure("test"):
            await asyncio.sleep(0)
        summary = profiler.summary()
        assert summary["test"]["count"] == 1.0

    asyncio.run(scenario())


def test_performance_recorder() -> None:
    recorder = PerformanceRecorder()
    recorder.retrieval("local", 0.1, items=3)
    recorder.database("select", 0.2, rows=4)
    recorder.memory(10.0)
    recorder.agent("planner", 0.3)
    recorder.model(ModelUsageMetric("test", "fast", 100, 50, 0.01))
    recorder.cost_per_task("drafting", 0.01)
