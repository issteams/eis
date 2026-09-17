from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from eis.observability import (
    ConcurrencyLimiter,
    HealthRegistry,
    JobStore,
    Observability,
    ProductionSettings,
    RetryPolicy,
    retry_async,
)


def test_metrics_capture_latency_and_failures() -> None:
    telemetry = Observability()
    with telemetry.measure("agent.run", agent="engineering"):
        pass
    samples = telemetry.metrics.snapshot()
    assert any(sample.name == "eis_operation_latency_seconds_count" for sample in samples)


def test_model_and_tool_metrics_are_tracked() -> None:
    telemetry = Observability()
    telemetry.record_tool("git", "success", 0.2)
    telemetry.record_verification("tests", "passed", 0.3)
    samples = telemetry.metrics.snapshot()
    assert any(sample.name == "eis_tool_executions_total" for sample in samples)
    assert any(sample.name == "eis_verifications_total" for sample in samples)


def test_prometheus_export() -> None:
    telemetry = Observability()
    telemetry.metrics.increment("eis_requests_total", component="api")
    output = telemetry.metrics.prometheus()
    assert "eis_requests_total" in output
    assert 'component="api"' in output


def test_health_readiness_degrades_safely() -> None:
    health = HealthRegistry()
    health.register("database", lambda: False)
    assert health.liveness()["status"] == "ok"
    assert health.readiness()["status"] == "not_ready"
    health.set_not_ready()
    assert health.readiness()["status"] == "not_ready"


def test_retry_is_bounded() -> None:
    attempts = 0

    async def operation() -> object:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("temporary")

    async def run() -> None:
        with pytest.raises(RuntimeError):
            await retry_async(operation, policy=RetryPolicy(max_retries=2, backoff_seconds=0))

    asyncio.run(run())
    assert attempts == 3


def test_concurrency_limiter() -> None:
    async def run() -> list[str]:
        limiter = ConcurrencyLimiter(1)
        order: list[str] = []

        async def work(name: str) -> None:
            async with limiter:
                order.append(f"start:{name}")
                await asyncio.sleep(0)
                order.append(f"end:{name}")

        await asyncio.gather(work("a"), work("b"))
        return order

    order = asyncio.run(run())
    assert order in (
        ["start:a", "end:a", "start:b", "end:b"],
        ["start:b", "end:b", "start:a", "end:a"],
    )


def test_job_store_recovers_interrupted_work(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.enqueue("agent", "payload")
    claimed = store.claim(lease_seconds=1)
    assert claimed is not None
    now = claimed.lease_until + 1 if claimed.lease_until else 2
    assert store.recover_expired(now=now) == 1
    recovered = store.claim(lease_seconds=30)
    assert recovered is not None
    assert recovered.attempts == 2
    store.complete(recovered.id)
    completed = store.get(recovered.id)
    assert completed is not None
    assert completed.status == "completed"
    assert job.id == completed.id


def test_job_store_failure_can_retry(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.enqueue("agent", "payload")
    claimed = store.claim()
    assert claimed is not None
    store.fail(job.id, "temporary failure", retry=True)
    failed = store.get(job.id)
    assert failed is not None
    assert failed.status == "queued"


def test_settings_validate() -> None:
    settings = ProductionSettings(worker_concurrency=2, max_concurrent_tasks=2)
    settings.validate()

    with pytest.raises(ValueError):
        ProductionSettings(request_timeout_seconds=0).validate()
