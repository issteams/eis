"""Low-overhead profiling helpers for EIS runtime components."""

from __future__ import annotations

import resource
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfileSample:
    operation: str
    latency_seconds: float
    memory_mib: float
    metadata: dict[str, str]


def process_memory_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024) if value > 10_000 else value / 1024


class PerformanceProfiler:
    """Collect component timings and process memory without altering execution semantics."""

    def __init__(self) -> None:
        self.samples: list[ProfileSample] = []

    @asynccontextmanager
    async def measure(self, operation: str, **metadata: str) -> AsyncIterator[None]:
        started = time.perf_counter()
        before = process_memory_mib()
        try:
            yield
        finally:
            self.samples.append(
                ProfileSample(
                    operation,
                    time.perf_counter() - started,
                    max(before, process_memory_mib()),
                    metadata,
                )
            )

    def summary(self) -> dict[str, dict[str, float]]:
        grouped: dict[str, list[ProfileSample]] = {}
        for sample in self.samples:
            grouped.setdefault(sample.operation, []).append(sample)
        result: dict[str, dict[str, float]] = {}
        for name, samples in grouped.items():
            latencies = sorted(item.latency_seconds for item in samples)
            result[name] = {
                "count": float(len(latencies)),
                "mean_seconds": sum(latencies) / len(latencies),
                "p50_seconds": latencies[len(latencies) // 2],
                "max_seconds": max(latencies),
                "max_memory_mib": max(item.memory_mib for item in samples),
            }
        return result
