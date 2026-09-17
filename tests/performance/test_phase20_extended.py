from __future__ import annotations

import asyncio

import pytest

from eis.models.interfaces import GenerationRequest, ModelMetadata
from eis.observability.models import ModelUsageMetric
from eis.observability.performance import PerformanceRecorder
from eis.observability.runtime import Observability
from eis.performance.cache import AsyncResponseCache
from eis.performance.context import ContextBudget
from eis.performance.execution import RetryConfig, batch_gather, retry_optimized
from eis.performance.profiler import PerformanceProfiler, process_memory_mib
from eis.performance.routing import ModelRoute, ModelRouter, RoutingPolicy
from eis.performance.scheduler import TaskScheduler


class FakeModel:
    metadata = ModelMetadata("test", "fast")


def test_cache_eviction_and_uncacheable() -> None:
    async def scenario() -> None:
        cache: AsyncResponseCache[str] = AsyncResponseCache(max_entries=1, ttl_seconds=10)
        calls = 0

        async def factory() -> str:
            nonlocal calls
            calls += 1
            return str(calls)

        assert await cache.get_or_set("a", factory) == "1"
        assert await cache.get_or_set("b", factory) == "2"
        assert await cache.get("a") is None
        assert await cache.get_or_set("c", factory, cacheable=False) == "3"
        await cache.clear()
        assert cache.stats().evictions == 1

    asyncio.run(scenario())


def test_cache_factory_failure_propagates() -> None:
    async def scenario() -> None:
        cache: AsyncResponseCache[str] = AsyncResponseCache()

        async def factory() -> str:
            raise ValueError("bad")

        with pytest.raises(ValueError):
            await cache.get_or_set("bad", factory)

    asyncio.run(scenario())


def test_context_budget_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        ContextBudget(max_items=0)
    with pytest.raises(ValueError):
        ContextBudget(max_characters=10, reserve_characters=10)


def test_router_explicit_model_and_cost() -> None:
    fast = FakeModel()
    slow = FakeModel()
    slow.metadata = ModelMetadata("test", "slow")
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
    with pytest.raises(ValueError):
        ModelRouter(
            [ModelRoute("fast", model)],
            RoutingPolicy(default_route="fast", task_routes={"x": "missing"}),
        )


def test_retry_fails_fast_for_non_retryable() -> None:
    async def scenario() -> None:
        async def operation() -> int:
            raise ValueError("permanent")

        with pytest.raises(ValueError):
            await retry_optimized(operation, retryable=lambda _: False)

    asyncio.run(scenario())


def test_retry_config_and_batch_validation() -> None:
    with pytest.raises(ValueError):
        RetryConfig(max_attempts=0)

    async def scenario() -> None:
        async def operation() -> int:
            return 1

        with pytest.raises(ValueError):
            await batch_gather([operation], batch_size=0)

    asyncio.run(scenario())


def test_scheduler_close_without_start() -> None:
    async def scenario() -> None:
        scheduler = TaskScheduler()
        await scheduler.close()
        assert scheduler.queued == 0

    asyncio.run(scenario())


def test_profiler_collects_summary() -> None:
    async def scenario() -> None:
        profiler = PerformanceProfiler()
        async with profiler.measure("test", component="unit"):
            await asyncio.sleep(0)
        summary = profiler.summary()
        assert summary["test"]["count"] == 1.0
        assert summary["test"]["p50_seconds"] >= 0

    asyncio.run(scenario())
    assert process_memory_mib() >= 0


def test_performance_recorder_writes_metrics() -> None:
    observability = Observability()
    recorder = PerformanceRecorder(observability)
    recorder.retrieval("memory", 0.1, items=3)
    recorder.database("select", 0.2, rows=4)
    recorder.memory(32.0)
    recorder.agent("test", 0.3)
    recorder.model(ModelUsageMetric("test", "fast", 10, 5, 15, 0.01, "USD", 0.4, True))
    recorder.cost_per_task("test", 0.02)
    names = {sample.name for sample in observability.metrics.snapshot()}
    assert "eis_retrieval_latency_seconds_count" in names
    assert "eis_database_latency_seconds_count" in names
    assert "eis_process_memory_mib" in names
    assert "eis_model_tokens_total" in names
    assert "eis_cost_per_task_count" in names
