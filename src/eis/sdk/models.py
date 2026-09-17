"""Stable public data contracts for the EIS SDK.

These models are intentionally independent from EIS runtime internals. Internal
implementations may evolve without changing these contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Product:
    """A product registered with an EIS instance."""

    name: str
    purpose: str
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    """Knowledge stored through the stable SDK surface."""

    content: str
    source: str
    title: str | None = None
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """Memory stored through the stable SDK surface."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class Task:
    """A user-visible EIS task."""

    objective: str
    id: UUID = field(default_factory=uuid4)
    input: Any = None


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Stable task execution result."""

    task_id: UUID
    status: TaskStatus
    output: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Stable result returned by an SDK agent run."""

    agent: str
    task: Task
    output: Any = None
    error: str | None = None
    completed: bool = False


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Structured result of evaluating an idea or decision."""

    subject: str
    conclusion: str
    rationale: str
    evidence: tuple[str, ...] = ()
    uncertainty: str | None = None


@dataclass(frozen=True, slots=True)
class EngineeringResult:
    """Stable wrapper around an engineering execution result."""

    task: Task
    status: str
    summary: str
    raw: Any = None


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Stable result of a tool or execution adapter call."""

    action: str
    success: bool
    output: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """Stable result of an orchestration adapter call."""

    workflow: str
    success: bool
    output: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """SDK-safe representation of an audit event."""

    action: str
    result: str
    timestamp: str
    task_id: str | None = None
    agent: str | None = None
    target: str | None = None
    failure: str | None = None


__all__ = [
    "AgentResult",
    "AuditEntry",
    "EngineeringResult",
    "EvaluationResult",
    "ExecutionResult",
    "KnowledgeItem",
    "MemoryItem",
    "Product",
    "Task",
    "TaskResult",
    "TaskStatus",
    "WorkflowResult",
]
