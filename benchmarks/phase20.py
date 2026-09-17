"""Phase 20 reproducible local benchmark suite.

Run with:
    python -m benchmarks.phase20

The suite deliberately uses local deterministic doubles for model/tool/agent timing so
CI remains network-independent. Production runs should additionally feed provider timings
through EIS observability metrics; no benchmark result here represents external-provider
latency.
"""

from __future__ import annotations

import asyncio
import json
import resource
import sqlite3
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path

from eis.context.models import ContextItem, ProvenanceRecord, Query, SourceKind
from eis.context.retrieval import InMemoryRetriever, QueryNormalizer
from eis.performance.context import approximate_tokens, optimize_context
from eis.performance.execution import batch_gather
from eis.performance.scheduler import Priority, TaskScheduler


@dataclass(frozen=True, slots=True)
class Measurement:
    name: str
    seconds: float
    value: float | None = None
    unit: str | None = None


async def _timed(name: str, operation):
    started = time.perf_counter()
    value = await operation()
    return Measurement(name, time.perf_counter() - started, value)


async def benchmark_retrieval() -> Measurement:
    provenance = ProvenanceRecord("bench", SourceKind.KNOWLEDGE, "bench://local")
    items = [ContextItem.create(f"EIS engineering evidence item {i} retrieval correctness", provenance) for i in range(1000)]
    retriever = InMemoryRetriever(items)
    query = QueryNormalizer().normalize("engineering retrieval correctness")
    result = await _timed("retrieval_latency", lambda: retriever.retrieve(query, limit=20))
    return Measurement(result.name, result.seconds, 20, "items")


async def benchmark_model() -> Measurement:
    async def local_model() -> str:
        await asyncio.sleep(0)
        return "deterministic model response"

    result = await _timed("model_latency_local", local_model)
    return Measurement(result.name, result.seconds, 1, "request")


async def benchmark_agent() -> Measurement:
    async def agent() -> None:
        for _ in range(8):
            await asyncio.sleep(0)

    result = await _timed("agent_execution", agent)
    return Measurement(result.name, result.seconds, 8, "steps")


async def benchmark_tool() -> Measurement:
    async def tool() -> int:
        return sum(range(1000))

    result = await _timed("tool_execution", tool)
    return Measurement(result.name, result.seconds, 1000, "iterations")


def benchmark_memory() -> Measurement:
    tracemalloc.start()
    _ = ["eis-performance" * 32 for _ in range(5000)]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return Measurement("memory_peak", 0.0, peak / (1024 * 1024), "MiB")


def benchmark_database() -> Measurement:
    started = time.perf_counter()
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, content TEXT NOT NULL)")
        db.executemany("INSERT INTO evidence(content) VALUES (?)", ((f"item-{i}",) for i in range(1000)))
        db.execute("CREATE INDEX evidence_content_idx ON evidence(content)")
        rows = db.execute("SELECT COUNT(*) FROM evidence WHERE content LIKE 'item-%'").fetchone()[0]
    return Measurement("database_query", time.perf_counter() - started, float(rows), "rows")


async def benchmark_concurrency() -> Measurement:
    async def operation() -> int:
        await asyncio.sleep(0.001)
        return 1

    operations = [lambda: operation() for _ in range(32)]
    started = time.perf_counter()
    await batch_gather(operations, batch_size=8)
    elapsed = time.perf_counter() - started
    return Measurement("bounded_concurrency", elapsed, 8, "batch_size")


async def benchmark_scheduler() -> Measurement:
    scheduler = TaskScheduler(workers=4, max_queue=16)
    started = time.perf_counter()
    await asyncio.gather(*(scheduler.submit(asyncio.sleep(0), priority=Priority.NORMAL) for _ in range(16)))
    await scheduler.close()
    return Measurement("task_scheduler", time.perf_counter() - started, 4, "workers")


def benchmark_context() -> Measurement:
    provenance = ProvenanceRecord("bench", SourceKind.KNOWLEDGE, "bench://context", authority=1.0)
    items = [ContextItem.create(f"evidence {i} " + "x" * 500, provenance, relevance=1 - i / 100) for i in range(100)]
    started = time.perf_counter()
    optimized = optimize_context(items)
    elapsed = time.perf_counter() - started
    return Measurement("context_optimization", elapsed, approximate_tokens(optimized), "estimated_tokens")


def benchmark_cost() -> Measurement:
    input_tokens, output_tokens = 2400, 700
    input_price, output_price = 0.15, 0.60
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    return Measurement("cost_per_task", 0.0, cost, "USD")


def benchmark_memory_rss() -> Measurement:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    mib = rss / (1024 * 1024) if rss > 10_000 else rss / 1024
    return Measurement("process_max_rss", 0.0, mib, "MiB")


async def main() -> None:
    measurements = [
        await benchmark_retrieval(),
        await benchmark_model(),
        await benchmark_agent(),
        await benchmark_tool(),
        benchmark_memory(),
        benchmark_memory_rss(),
        benchmark_database(),
        await benchmark_concurrency(),
        await benchmark_scheduler(),
        benchmark_context(),
        benchmark_cost(),
    ]
    payload = {"measurements": [asdict(item) for item in measurements]}
    output = Path("benchmark-results/phase20.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
