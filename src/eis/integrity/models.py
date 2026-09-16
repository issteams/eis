from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from eis.knowledge.models import Provenance


class IntegrityKind(StrEnum):
    FACT = "fact"
    VERIFIED_FACT = "verified_fact"
    OBSERVATION = "observation"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"
    OPINION = "opinion"
    PROPOSAL = "proposal"
    UNKNOWN = "unknown"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNCERTAIN = "uncertain"


class ValidationStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    QUESTIONABLE = "questionable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    TECHNICALLY_RISKY = "technically_risky"
    NEEDS_INVESTIGATION = "needs_investigation"


@dataclass(frozen=True, slots=True)
class Confidence:
    value: float
    basis: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.basis.strip():
            raise ValueError("confidence basis must not be empty")


@dataclass(frozen=True, slots=True)
class Uncertainty:
    reason: str
    impact: str
    resolution: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    content: str
    provenance: Provenance
    kind: IntegrityKind = IntegrityKind.FACT
    confidence: Confidence = field(
        default_factory=lambda: Confidence(1.0, "source evidence")
    )
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    claim_key: str | None = None
    polarity: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_fresh(self) -> bool:
        now = datetime.now(UTC)
        return self.expires_at is None or now <= self.expires_at


@dataclass(frozen=True, slots=True)
class Claim:
    statement: str
    kind: IntegrityKind
    confidence: Confidence
    provenance: tuple[Provenance, ...] = ()
    evidence_ids: tuple[UUID, ...] = ()
    uncertainty: tuple[Uncertainty, ...] = ()
    invalidators: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class ClaimAssessment:
    claim: Claim
    status: ValidationStatus
    supporting_evidence: tuple[EvidenceItem, ...] = ()
    contradicting_evidence: tuple[EvidenceItem, ...] = ()
    unsupported_reasons: tuple[str, ...] = ()
    uncertainty: tuple[Uncertainty, ...] = ()
    freshness_checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class HonestResponse:
    answer: str
    known: tuple[Claim, ...]
    beliefs: tuple[Claim, ...]
    evidence: tuple[EvidenceItem, ...]
    uncertainties: tuple[Uncertainty, ...]
    invalidators: tuple[str, ...]
    assessments: tuple[ClaimAssessment, ...] = ()


@dataclass(frozen=True, slots=True)
class IdeaCriterion:
    name: str
    assessment: ClaimAssessment


@dataclass(frozen=True, slots=True)
class IdeaEvaluation:
    idea: str
    objective: str
    criteria: tuple[IdeaCriterion, ...]
    status: ValidationStatus
    risks: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    next_investigations: tuple[str, ...] = ()


__all__ = [
    "Claim",
    "ClaimAssessment",
    "Confidence",
    "EvidenceItem",
    "HonestResponse",
    "IdeaCriterion",
    "IdeaEvaluation",
    "IntegrityKind",
    "Uncertainty",
    "ValidationStatus",
]
