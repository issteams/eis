"""Models for independent verification and bounded self-correction."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class VerificationStage(StrEnum):
    REQUIREMENT = "requirement"
    CODE = "code"
    TEST = "test"
    REGRESSION = "regression"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    QUALITY = "quality"


class FailureClass(StrEnum):
    SYNTAX = "syntax"
    TYPE = "type"
    TEST = "test"
    RUNTIME = "runtime"
    DEPENDENCY = "dependency"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    REQUIREMENT = "requirement"
    ENVIRONMENT = "environment"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VerificationLimits:
    max_correction_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_correction_attempts < 0:
            raise ValueError("max_correction_attempts must not be negative")


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    objective: str
    repository: str
    changes: tuple[str, ...] = ()
    baseline: Any = None
    input: Any = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class StageResult:
    stage: VerificationStage
    passed: bool
    detail: str = ""
    evidence: tuple[str, ...] = ()
    uncertainty: str = ""


@dataclass(frozen=True, slots=True)
class RootCauseAnalysis:
    failure: str
    classification: FailureClass
    suspected_cause: str
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class CorrectionRecord:
    attempt: int
    original_failure: str
    classification: FailureClass
    suspected_cause: str
    change_made: tuple[str, ...] = ()
    validation_result: str = ""
    remaining_uncertainty: str = ""
    root_cause: RootCauseAnalysis | None = None


@dataclass(frozen=True, slots=True)
class VerificationReport:
    status: str
    stages: tuple[StageResult, ...] = ()
    corrections: tuple[CorrectionRecord, ...] = ()
    failures: tuple[str, ...] = ()
    attempts: int = 0
    escalated: bool = False
    escalation_reason: str | None = None
    summary: str = ""

    @property
    def verified(self) -> bool:
        if self.status != "verified" or self.escalated:
            return False
        latest: dict[VerificationStage, StageResult] = {}
        for stage in self.stages:
            latest[stage.stage] = stage
        return bool(latest) and all(stage.passed for stage in latest.values())
