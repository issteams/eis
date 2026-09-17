"""Standardized performance measurements for EIS components."""

from __future__ import annotations

from eis.observability.models import ModelUsageMetric, TaskMetric
from eis.observability.runtime import Observability


class PerformanceRecorder:
    """Map Phase 20 measurements onto the existing EIS metrics registry."""

    def __init__(self, observability: Observability | None = None) -> None:
        self.observability = observability or Observability()

    def retrieval(self, backend: str, latency_seconds: float, *, items: int) -> None:
        self.observability.metrics.observe(
            "eis_retrieval_latency_seconds", latency_seconds, backend=backend
        )
        self.observability.metrics.increment("eis_retrieval_items_total", items, backend=backend)

    def database(self, operation: str, latency_seconds: float, *, rows: int = 0) -> None:
        self.observability.metrics.observe(
            "eis_database_latency_seconds", latency_seconds, operation=operation
        )
        self.observability.metrics.increment("eis_database_rows_total", rows, operation=operation)

    def memory(self, value_mib: float) -> None:
        self.observability.metrics.set_gauge("eis_process_memory_mib", value_mib)

    def agent(self, task_type: str, latency_seconds: float, status: str = "completed") -> None:
        self.observability.record_task(TaskMetric(task_type, status, latency_seconds))

    def model(self, metric: ModelUsageMetric) -> None:
        self.observability.record_model_usage(metric)

    def cost_per_task(self, task_type: str, cost: float, currency: str = "USD") -> None:
        self.observability.metrics.observe(
            "eis_cost_per_task", cost, task_type=task_type, currency=currency
        )
