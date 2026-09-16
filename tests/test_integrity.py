from datetime import UTC, datetime, timedelta

import pytest

from eis.integrity import (
    Claim,
    Confidence,
    DefaultIntegrityEngine,
    EvidenceItem,
    IntegrityKind,
    SimpleConfidenceCalibrator,
    Uncertainty,
    ValidationStatus,
)
from eis.knowledge.models import KnowledgeSource, Provenance


def make_evidence(
    content: str,
    *,
    claim_key: str = "python-version",
    polarity: bool | None = True,
    source: str = "repo/README.md",
    kind: IntegrityKind = IntegrityKind.FACT,
    expires_at: datetime | None = None,
) -> EvidenceItem:
    provenance = Provenance.capture(KnowledgeSource.create("document", source))
    return EvidenceItem(
        content=content,
        provenance=provenance,
        kind=kind,
        confidence=Confidence(0.9, "documented source"),
        claim_key=claim_key,
        polarity=polarity,
        expires_at=expires_at,
    )


def make_claim(
    statement: str = "The project uses Python 3.12",
    *,
    kind: IntegrityKind = IntegrityKind.FACT,
    claim_key: str = "python-version",
    polarity: bool = True,
) -> Claim:
    return Claim(
        statement=statement,
        kind=kind,
        confidence=Confidence(0.7, "initial assessment"),
        metadata={"claim_key": claim_key, "polarity": polarity},
    )


def test_supported_claim_requires_attributable_support() -> None:
    engine = DefaultIntegrityEngine()
    assessment = engine.validate_claim(
        make_claim(), [make_evidence("pyproject requires Python 3.12")]
    )
    assert assessment.status is ValidationStatus.SUPPORTED
    assert len(assessment.supporting_evidence) == 1
    assert assessment.supporting_evidence[0].provenance.source.locator == "repo/README.md"


def test_missing_evidence_never_becomes_supported() -> None:
    engine = DefaultIntegrityEngine()
    assessment = engine.validate_claim(make_claim(), [])
    assert assessment.status is ValidationStatus.INSUFFICIENT_EVIDENCE
    assert assessment.unsupported_reasons


def test_unrelated_evidence_is_not_support() -> None:
    engine = DefaultIntegrityEngine()
    assessment = engine.validate_claim(
        make_claim(), [make_evidence("the project uses PostgreSQL", claim_key="database")]
    )
    assert assessment.status is ValidationStatus.INSUFFICIENT_EVIDENCE


def test_contradicting_fresh_evidence_is_questionable() -> None:
    engine = DefaultIntegrityEngine()
    evidence = [
        make_evidence("documentation says Python 3.12", source="docs/runtime.md"),
        make_evidence(
            "deployment configuration uses Python 3.11",
            source="deploy/runtime.yml",
            polarity=False,
        ),
    ]
    assessment = engine.validate_claim(make_claim(), evidence)
    assert assessment.status is ValidationStatus.QUESTIONABLE
    assert len(assessment.supporting_evidence) == 1
    assert len(assessment.contradicting_evidence) == 1
    assert assessment.uncertainty


def test_stale_evidence_does_not_create_fresh_certainty() -> None:
    engine = DefaultIntegrityEngine()
    expired = datetime.now(UTC) - timedelta(seconds=1)
    assessment = engine.validate_claim(
        make_claim(), [make_evidence("old deployment", expires_at=expired)]
    )
    assert assessment.status is ValidationStatus.INSUFFICIENT_EVIDENCE
    assert assessment.uncertainty


def test_verified_fact_requires_independent_sources() -> None:
    engine = DefaultIntegrityEngine()
    one_source = engine.validate_claim(
        make_claim(kind=IntegrityKind.VERIFIED_FACT),
        [make_evidence("source A")],
    )
    assert one_source.status is ValidationStatus.QUESTIONABLE
    two_sources = engine.validate_claim(
        make_claim(kind=IntegrityKind.VERIFIED_FACT),
        [
            make_evidence("source A", source="a.md"),
            make_evidence("source B", source="b.md"),
        ],
    )
    assert two_sources.status is ValidationStatus.SUPPORTED


def test_confidence_is_explicit_and_bounded() -> None:
    with pytest.raises(ValueError):
        Confidence(1.1, "bad")
    with pytest.raises(ValueError):
        Confidence(0.5, "")


def test_honest_response_separates_supported_and_unsettled_claims() -> None:
    engine = DefaultIntegrityEngine()
    supported = make_claim()
    unsupported = make_claim("The project has ten production regions", claim_key="regions")
    response = engine.assess_response(
        "Current evidence supports the runtime claim but not the region claim.",
        [supported, unsupported],
        [make_evidence("Python 3.12", claim_key="python-version")],
    )
    assert response.known == (supported,)
    assert response.beliefs == (unsupported,)
    assert response.assessments[1].status is ValidationStatus.INSUFFICIENT_EVIDENCE


def test_invalidators_are_preserved_for_future_reassessment() -> None:
    engine = DefaultIntegrityEngine()
    claim = Claim(
        statement="The current architecture is sufficient",
        kind=IntegrityKind.INFERENCE,
        confidence=Confidence(0.6, "limited evidence"),
        invalidators=("new scale requirement", "security finding"),
    )
    response = engine.assess_response("tentative conclusion", [claim], [])
    assert response.invalidators == ("new scale requirement", "security finding")


def test_idea_evaluation_exposes_unknowns_risks_and_dependencies() -> None:
    engine = DefaultIntegrityEngine()
    supported = engine.validate_claim(make_claim(), [make_evidence("runtime evidence")])
    risky_claim = make_claim("The proposed integration introduces a security risk", claim_key="security")
    risky_claim = Claim(
        statement=risky_claim.statement,
        kind=IntegrityKind.INFERENCE,
        confidence=risky_claim.confidence,
        metadata={"claim_key": "security", "polarity": True, "risk": True},
    )
    risky = engine.validate_claim(
        risky_claim,
        [make_evidence("security review found an integration risk", claim_key="security")],
    )
    evaluation = engine.evaluate_idea(
        "Add the integration",
        "Reduce manual deployment work",
        [supported, risky],
    )
    assert evaluation.status is ValidationStatus.SUPPORTED
    assert evaluation.risks == (risky.claim.statement,)


def test_idea_with_missing_evidence_needs_investigation() -> None:
    engine = DefaultIntegrityEngine()
    assessment = engine.validate_claim(
        make_claim("The idea will scale to ten million users", claim_key="scale"), []
    )
    evaluation = engine.evaluate_idea(
        "Launch the idea", "Serve more users", [assessment]
    )
    assert evaluation.status is ValidationStatus.NEEDS_INVESTIGATION
    assert evaluation.unknowns == (assessment.claim.statement,)


def test_calibrator_is_a_hook_not_a_truth_source() -> None:
    calibrator = SimpleConfidenceCalibrator()
    assert calibrator.calibrate(0.8, outcome=True) == 0.85
    assert calibrator.calibrate(0.1, outcome=False) == 0.05
    with pytest.raises(ValueError):
        calibrator.calibrate(-0.1, outcome=True)


def test_uncertainty_can_define_resolution_path() -> None:
    uncertainty = Uncertainty(
        "source versions disagree",
        "the conclusion may change",
        "compare the source revisions",
    )
    assert uncertainty.resolution == "compare the source revisions"
