"""Models for repository-aware autonomous engineering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class EngineeringPhase(StrEnum):
    UNDERSTAND = "understand"
    RETRIEVE = "retrieve"
    INSPECT = "inspect"
    ARCHITECTURE = "architecture"
    AFFECTED_COMPONENTS = "affected_components"
    EXISTING_FUNCTIONALITY = "existing_functionality"
    DUPLICATION = "duplication"
    PLAN = "plan"
    VALIDATE_PLAN = "validate_plan"
    IMPLEMENT = "implement"
    TARGETED_TESTS = "targeted_tests"
    BROADER_TESTS = "broader_tests"
    ANALYZE_FAILURES = "analyze_failures"
    CORRECT = "correct"
    REPORT = "report"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class EngineeringLimits:
    max_iterations: int = 3
    max_files_changed: int = 10
    max_execution_seconds: float = 600.0
    max_tool_calls: int = 40

    def __post_init__(self) -> None:
        if self.max_iterations < 1 or self.max_files_changed < 1:
            raise ValueError("engineering limits must be positive")
        if self.max_execution_seconds <= 0 or self.max_tool_calls < 1:
            raise ValueError("engineering limits must be positive")


@dataclass(frozen=True, slots=True)
class EngineeringTask:
    objective: str
    repository: str
    input: Any = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class FileChange:
    path: str
    operation: str
    summary: str = ""


@dataclass(frozen=True, slots=True)
class ChangeRecord:
    phase: EngineeringPhase
    changes: tuple[FileChange, ...] = ()
    tool: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    repository: str
    files: tuple[str, ...] = ()
    architecture: tuple[str, ...] = ()
    existing_functionality: tuple[str, ...] = ()
    relevant_sources: tuple[str, ...] = ()
    duplicated_components: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineeringPlan:
    objective: str
    rationale: str
    affected_components: tuple[str, ...]
    reuse_candidates: tuple[str, ...]
    steps: tuple[str, ...]
    validation: tuple[str, ...]
    risks: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EngineeringReport:
    task: EngineeringTask
    status: str
    plan: EngineeringPlan | None = None
    changes: tuple[ChangeRecord, ...] = ()
    tests: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    iterations: int = 0
    tool_calls: int = 0
    escalated: bool = False
    escalation_reason: str | None = None
    summary: str = ""
