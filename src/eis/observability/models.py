"""Production observability value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class LogEvent:
    level: str
    event: str
    fields: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class SpanRecord:
    trace_id: str
    span_id: str
    name: str
    started_at: datetime
    ended_at: datetime
    attributes: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def latency_seconds(self) -> float:
        return max(0.0, (self.ended_at - self.started_at).total_seconds())


@dataclass(frozen=True, slots=True)
class ModelUsageMetric:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float | None
    currency: str | None
    latency_seconds: float
    success: bool


@dataclass(frozen=True, slots=True)
class TaskMetric:
    task_type: str
    status: str
    latency_seconds: float
    retries: int = 0


__all__ = [
    "LogEvent",
    "MetricSample",
    "ModelUsageMetric",
    "SpanRecord",
    "TaskMetric",
    "TraceContext",
    "utc_now",
]
