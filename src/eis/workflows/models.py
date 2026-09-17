"""Persistent models for end-to-end autonomous engineering workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class WorkflowPhase(StrEnum):
    UNDERSTAND = "understand"
    RETRIEVE_KNOWLEDGE = "retrieve_knowledge"
    INSPECT_PRODUCT = "inspect_product"
    EVALUATE_IDEA = "evaluate_idea"
    IDENTIFY_RISKS = "identify_risks"
    CREATE_PLAN = "create_plan"
    ARCHITECTURE_REVIEW = "architecture_review"
    APPROVAL = "approval"
    IMPLEMENT = "implement"
    TEST = "test"
    DEBUG = "debug"
    CORRECT = "correct"
    SECURITY_REVIEW = "security_review"
    REQUIREMENT_VERIFICATION = "requirement_verification"
    DOCUMENT = "document"
    FINAL_REPORT = "final_report"


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class WorkflowRequest:
    objective: str
    repository: str
    input: Any = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("workflow objective must not be empty")
        if not self.repository.strip():
            raise ValueError("workflow repository must not be empty")


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    phase: WorkflowPhase
    status: str
    detail: str = ""
    evidence: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    corrections: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class WorkflowApproval:
    phase: WorkflowPhase
    resource: str
    reason: str
    approval_request_id: UUID


@dataclass(frozen=True, slots=True)
class WorkflowReport:
    request: WorkflowRequest
    status: WorkflowStatus
    events: tuple[WorkflowEvent, ...] = ()
    completed_work: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    corrections: tuple[str, ...] = ()
    remaining_risks: tuple[str, ...] = ()
    remaining_uncertainty: tuple[str, ...] = ()
    human_decisions: tuple[str, ...] = ()
    escalation_reason: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowState:
    request: WorkflowRequest
    status: WorkflowStatus = WorkflowStatus.PENDING
    phase_index: int = 0
    events: tuple[WorkflowEvent, ...] = ()
    approval: WorkflowApproval | None = None
    data: dict[str, Any] = field(default_factory=dict)
    escalation_reason: str | None = None

    @property
    def phase(self) -> WorkflowPhase | None:
        phases = tuple(WorkflowPhase)
        return phases[self.phase_index] if self.phase_index < len(phases) else None
