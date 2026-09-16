from __future__ import annotations

from collections.abc import Sequence

from eis.integrity.models import (
    Claim,
    ClaimAssessment,
    EvidenceItem,
    HonestResponse,
    IdeaCriterion,
    IdeaEvaluation,
    IntegrityKind,
    Uncertainty,
    ValidationStatus,
)


class InMemoryEvidenceTracker:
    """Deterministic evidence registry for tests and local integrity workflows."""

    def __init__(self) -> None:
        self._evidence: list[EvidenceItem] = []

    def track(self, evidence: EvidenceItem) -> None:
        self._evidence.append(evidence)

    def sources(self) -> Sequence[EvidenceItem]:
        return tuple(self._evidence)


class DefaultContradictionDetector:
    def find_contradictions(
        self,
        evidence: Sequence[EvidenceItem],
    ) -> tuple[tuple[EvidenceItem, EvidenceItem], ...]:
        pairs: list[tuple[EvidenceItem, EvidenceItem]] = []
        for index, first in enumerate(evidence):
            if first.claim_key is None or first.polarity is None or not first.is_fresh:
                continue
            for second in evidence[index + 1 :]:
                if (
                    second.claim_key == first.claim_key
                    and second.polarity is not None
                    and second.polarity is not first.polarity
                    and second.is_fresh
                ):
                    pairs.append((first, second))
        return tuple(pairs)


class DefaultProvenanceTracker:
    """In-memory provenance registry; persistence belongs to a later adapter."""

    def __init__(self) -> None:
        self._evidence: list[EvidenceItem] = []

    def record(self, evidence: EvidenceItem) -> None:
        self._evidence.append(evidence)

    def sources(self) -> Sequence[EvidenceItem]:
        return tuple(self._evidence)


class DefaultIntegrityEngine:
    """Deterministic integrity checks; no model provider is required."""

    def validate_claim(
        self,
        claim: Claim,
        evidence: Sequence[EvidenceItem],
    ) -> ClaimAssessment:
        matching = tuple(item for item in evidence if self._matches_claim(claim, item))
        fresh = tuple(item for item in matching if item.is_fresh)
        stale = tuple(item for item in matching if not item.is_fresh)
        supporting = tuple(item for item in fresh if self._supports(claim, item))
        contradicting = tuple(item for item in fresh if self._contradicts(claim, item))
        uncertainties = list(claim.uncertainty)
        reasons: list[str] = []

        if stale:
            uncertainties.append(
                Uncertainty(
                    "some matching evidence is stale",
                    "the conclusion may no longer reflect current conditions",
                    "refresh or replace the stale source",
                )
            )

        if contradicting:
            uncertainties.append(
                Uncertainty(
                    "fresh evidence conflicts with supporting evidence",
                    "the claim cannot be treated as settled",
                    "resolve the conflicting sources",
                )
            )
            status = ValidationStatus.QUESTIONABLE
        elif not supporting:
            if matching:
                reasons.append("available evidence does not support the claim")
                status = ValidationStatus.UNSUPPORTED
            else:
                reasons.append("no attributable evidence supports the claim")
                status = ValidationStatus.INSUFFICIENT_EVIDENCE
        elif (
            claim.kind is IntegrityKind.VERIFIED_FACT
            and len({item.provenance.source.source_id for item in supporting}) < 2
        ):
            uncertainties.append(
                Uncertainty(
                    "verification has only one independent source",
                    "the claim should not be treated as independently verified",
                    "obtain corroboration from another source",
                )
            )
            status = ValidationStatus.QUESTIONABLE
        elif claim.metadata.get("technical_risk"):
            status = ValidationStatus.TECHNICALLY_RISKY
        else:
            status = ValidationStatus.SUPPORTED

        return ClaimAssessment(
            claim=claim,
            status=status,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            unsupported_reasons=tuple(reasons),
            uncertainty=tuple(uncertainties),
        )

    def assess_response(
        self,
        answer: str,
        claims: Sequence[Claim],
        evidence: Sequence[EvidenceItem],
    ) -> HonestResponse:
        assessments = tuple(self.validate_claim(claim, evidence) for claim in claims)
        known = tuple(
            assessment.claim
            for assessment in assessments
            if assessment.status is ValidationStatus.SUPPORTED
        )
        beliefs = tuple(
            assessment.claim
            for assessment in assessments
            if assessment.status is not ValidationStatus.SUPPORTED
        )
        uncertainties = tuple(
            uncertainty for assessment in assessments for uncertainty in assessment.uncertainty
        )
        invalidators = tuple(invalidator for claim in claims for invalidator in claim.invalidators)
        return HonestResponse(
            answer=answer,
            known=known,
            beliefs=beliefs,
            evidence=tuple(evidence),
            uncertainties=uncertainties,
            invalidators=invalidators,
            assessments=assessments,
        )

    def evaluate_idea(
        self,
        idea: str,
        objective: str,
        criteria: Sequence[ClaimAssessment],
    ) -> IdeaEvaluation:
        criterion_records = tuple(IdeaCriterion(item.claim.statement, item) for item in criteria)
        risks = tuple(
            assessment.claim.statement
            for assessment in criteria
            if assessment.claim.metadata.get("risk")
            or assessment.claim.metadata.get("technical_risk")
        )
        unknowns = tuple(
            assessment.claim.statement
            for assessment in criteria
            if assessment.status
            in {
                ValidationStatus.INSUFFICIENT_EVIDENCE,
                ValidationStatus.NEEDS_INVESTIGATION,
            }
        )
        dependencies = tuple(
            str(assessment.claim.metadata["dependency"])
            for assessment in criteria
            if "dependency" in assessment.claim.metadata
        )
        investigations = tuple(
            uncertainty.resolution
            for assessment in criteria
            for uncertainty in assessment.uncertainty
            if uncertainty.resolution
        )

        statuses = {assessment.status for assessment in criteria}
        if ValidationStatus.TECHNICALLY_RISKY in statuses:
            status = ValidationStatus.TECHNICALLY_RISKY
        elif ValidationStatus.QUESTIONABLE in statuses:
            status = ValidationStatus.QUESTIONABLE
        elif ValidationStatus.UNSUPPORTED in statuses:
            status = ValidationStatus.UNSUPPORTED
        elif statuses & {
            ValidationStatus.INSUFFICIENT_EVIDENCE,
            ValidationStatus.NEEDS_INVESTIGATION,
        }:
            status = ValidationStatus.NEEDS_INVESTIGATION
        else:
            status = ValidationStatus.SUPPORTED

        return IdeaEvaluation(
            idea=idea,
            objective=objective,
            criteria=criterion_records,
            status=status,
            risks=risks,
            unknowns=unknowns,
            dependencies=dependencies,
            next_investigations=investigations,
        )

    @staticmethod
    def _matches_claim(claim: Claim, evidence: EvidenceItem) -> bool:
        claim_key = claim.metadata.get("claim_key")
        return claim_key is None or evidence.claim_key == claim_key

    @staticmethod
    def _supports(claim: Claim, evidence: EvidenceItem) -> bool:
        expected = claim.metadata.get("polarity", True)
        return evidence.polarity is None or evidence.polarity is expected

    @staticmethod
    def _contradicts(claim: Claim, evidence: EvidenceItem) -> bool:
        expected = claim.metadata.get("polarity", True)
        return evidence.polarity is not None and evidence.polarity is not expected


class DefaultFreshnessChecker:
    def is_fresh(self, evidence: EvidenceItem) -> bool:
        return evidence.is_fresh


class SimpleConfidenceCalibrator:
    """Small deterministic calibration hook, not a claim-truth estimator."""

    def calibrate(self, confidence: float, *, outcome: bool) -> float:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        step = 0.05
        adjusted = confidence + step if outcome else confidence - step
        return max(0.0, min(1.0, adjusted))


__all__ = [
    "DefaultContradictionDetector",
    "DefaultFreshnessChecker",
    "DefaultIntegrityEngine",
    "DefaultProvenanceTracker",
    "InMemoryEvidenceTracker",
    "SimpleConfidenceCalibrator",
]
