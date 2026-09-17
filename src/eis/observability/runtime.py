"""Low-dependency observability runtime for EIS services and workers."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import structlog

from eis.observability.models import (
    LogEvent,
    MetricSample,
    ModelUsageMetric,
    SpanRecord,
    TaskMetric,
    TraceContext,
    utc_now,
)


class MetricsRegistry:
    """In-process counters, gauges and histograms with Prometheus text output."""

    def __init__(self) -> None:
        self._counters: defaultdict[
            tuple[str, tuple[tuple[str, str], ...]], float
        ] = defaultdict(float)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: defaultdict[
            tuple[str, tuple[tuple[str, str], ...]], list[float]
        ] = defaultdict(list)

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
        return name, tuple(sorted(labels.items()))

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        self._counters[self._key(name, labels)] += value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        self._gauges[self._key(name, labels)] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        self._histograms[self._key(name, labels)].append(value)

    def snapshot(self) -> list[MetricSample]:
        now = utc_now()
        samples: list[MetricSample] = []
        for (name, labels), value in self._counters.items():
            samples.append(MetricSample(name, value, dict(labels), now))
        for (name, labels), value in self._gauges.items():
            samples.append(MetricSample(name, value, dict(labels), now))
        for (name, labels), values in self._histograms.items():
            if values:
                samples.append(MetricSample(f"{name}_count", float(len(values)), dict(labels), now))
                samples.append(MetricSample(f"{name}_sum", sum(values), dict(labels), now))
        return samples

    def prometheus(self) -> str:
        lines: list[str] = []
        for sample in self.snapshot():
            labels = ""
            if sample.labels:
                rendered = []
                for key, value in sorted(sample.labels.items()):
                    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                    rendered.append(f'{key}="{escaped}"')
                labels = "{" + ",".join(rendered) + "}"
            lines.append(f"{sample.name}{labels} {sample.value}")
        return "\n".join(lines) + ("\n" if lines else "")


class StructuredLogger:
    """Structured JSON logging with safe context propagation."""

    def __init__(self, name: str = "eis", *, json_output: bool = True) -> None:
        renderer = (
            structlog.processors.JSONRenderer()
            if json_output
            else structlog.dev.ConsoleRenderer()
        )
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                renderer,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            cache_logger_on_first_use=False,
        )
        self._logger = structlog.get_logger(name)

    def log(self, level: str, event: str, **fields: Any) -> LogEvent:
        getattr(self._logger, level, self._logger.info)(event, **fields)
        return LogEvent(level, event, fields)


@dataclass(slots=True)
class Tracer:
    """Small tracing implementation; exporters can consume completed spans."""

    spans: list[SpanRecord] = field(default_factory=list)

    @contextmanager
    def span(
        self,
        name: str,
        context: TraceContext | None = None,
        **attributes: Any,
    ) -> Iterator[TraceContext]:
        trace_id = context.trace_id if context else uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        child = TraceContext(trace_id, span_id, context.span_id if context else None)
        started = utc_now()
        error: str | None = None
        try:
            yield child
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            self.spans.append(
                SpanRecord(trace_id, span_id, name, started, utc_now(), attributes, error)
            )


@dataclass(slots=True)
class Observability:
    """Shared instrumentation facade used by agents, tools, models and workers."""

    logger: StructuredLogger = field(default_factory=StructuredLogger)
    metrics: MetricsRegistry = field(default_factory=MetricsRegistry)
    tracer: Tracer = field(default_factory=Tracer)

    @contextmanager
    def measure(self, operation: str, **labels: str) -> Iterator[TraceContext]:
        started = time.monotonic()
        with self.tracer.span(operation, context=None, **labels) as context:
            try:
                yield context
            except Exception:
                self.metrics.increment(
                    "eis_failures_total", value=1.0, operation=operation, **labels
                )
                raise
            finally:
                self.metrics.observe(
                    "eis_operation_latency_seconds",
                    time.monotonic() - started,
                    operation=operation,
                    **labels,
                )

    def record_model_usage(self, usage: ModelUsageMetric) -> None:
        labels = {"provider": usage.provider, "model": usage.model}
        self.metrics.increment("eis_model_requests_total", value=1.0, **labels)
        self.metrics.increment("eis_model_input_tokens_total", value=usage.input_tokens, **labels)
        self.metrics.increment("eis_model_output_tokens_total", value=usage.output_tokens, **labels)
        self.metrics.increment("eis_model_tokens_total", value=usage.total_tokens, **labels)
        self.metrics.observe("eis_model_latency_seconds", usage.latency_seconds, **labels)
        if usage.estimated_cost is not None:
            self.metrics.increment(
                "eis_model_cost_total",
                value=usage.estimated_cost,
                currency=usage.currency or "UNKNOWN",
                **labels,
            )
        if not usage.success:
            self.metrics.increment("eis_model_failures_total", value=1.0, **labels)

    def record_task(self, metric: TaskMetric) -> None:
        self.metrics.increment(
            "eis_tasks_total",
            value=1.0,
            task_type=metric.task_type,
            status=metric.status,
        )
        self.metrics.observe(
            "eis_task_latency_seconds", metric.latency_seconds, task_type=metric.task_type
        )
        self.metrics.increment(
            "eis_task_retries_total", value=metric.retries, task_type=metric.task_type
        )

    def record_tool(self, tool: str, status: str, latency_seconds: float) -> None:
        self.metrics.increment(
            "eis_tool_executions_total", value=1.0, tool=tool, status=status
        )
        self.metrics.observe("eis_tool_latency_seconds", latency_seconds, tool=tool)
        if status not in {"success", "completed"}:
            self.metrics.increment("eis_tool_failures_total", value=1.0, tool=tool, status=status)

    def record_verification(self, stage: str, status: str, latency_seconds: float) -> None:
        self.metrics.increment(
            "eis_verifications_total", value=1.0, stage=stage, status=status
        )
        self.metrics.observe("eis_verification_latency_seconds", latency_seconds, stage=stage)
        if status not in {"passed", "success"}:
            self.metrics.increment(
                "eis_verification_failures_total", value=1.0, stage=stage, status=status
            )

    def health_snapshot(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "metrics": len(self.metrics.snapshot()),
            "spans": len(self.tracer.spans),
        }

    def dashboard(self) -> dict[str, Any]:
        return {
            "health": self.health_snapshot(),
            "metrics": [
                {"name": sample.name, "value": sample.value, "labels": sample.labels}
                for sample in self.metrics.snapshot()
            ],
            "recent_spans": [
                {
                    "trace_id": span.trace_id,
                    "name": span.name,
                    "latency_seconds": span.latency_seconds,
                    "error": span.error,
                }
                for span in self.tracer.spans[-50:]
            ],
        }


__all__ = ["MetricsRegistry", "Observability", "StructuredLogger", "Tracer"]
