from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from eis.integrity.models import (
    Claim,
    ClaimAssessment,
    EvidenceItem,
    HonestResponse,
    IdeaEvaluation,
)


class IntegrityEngine(Protocol):
    def validate_claim(
        self,
        claim: Claim,
        evidence: Sequence[EvidenceItem],
    ) -> ClaimAssessment: ...

    def assess_response(
        self,
        answer: str,
        claims: Sequence[Claim],
        evidence: Sequence[EvidenceItem],
    ) -> HonestResponse: ...

    def evaluate_idea(
        self,
        idea: str,
        objective: str,
        criteria: Sequence[ClaimAssessment],
    ) -> IdeaEvaluation: ...


class EvidenceTracker(Protocol):
    def track(self, evidence: EvidenceItem) -> None: ...

    def sources(self) -> Sequence[EvidenceItem]: ...


class ClaimValidator(Protocol):
    def validate_claim(
        self,
        claim: Claim,
        evidence: Sequence[EvidenceItem],
    ) -> ClaimAssessment: ...


class ContradictionDetector(Protocol):
    def find_contradictions(
        self,
        evidence: Sequence[EvidenceItem],
    ) -> tuple[tuple[EvidenceItem, EvidenceItem], ...]: ...


class FreshnessChecker(Protocol):
    def is_fresh(self, evidence: EvidenceItem) -> bool: ...


class ConfidenceCalibrator(Protocol):
    def calibrate(self, confidence: float, *, outcome: bool) -> float: ...


class ProvenanceTracker(Protocol):
    def record(self, evidence: EvidenceItem) -> None: ...


__all__ = [
    "ClaimValidator",
    "ConfidenceCalibrator",
    "ContradictionDetector",
    "EvidenceTracker",
    "FreshnessChecker",
    "IntegrityEngine",
    "ProvenanceTracker",
]
