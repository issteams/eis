"""Independent verification and bounded self-correction runtime."""

from __future__ import annotations

from dataclasses import dataclass

from eis.verification.models import (
    CorrectionRecord,
    FailureClass,
    RootCauseAnalysis,
    StageResult,
    VerificationLimits,
    VerificationReport,
    VerificationRequest,
    VerificationStage,
)
from eis.verification.protocols import (
    CorrectionRunner,
    RegressionGuard,
    RootCauseAnalyzer,
    StageVerifier,
)


class VerificationEscalation(RuntimeError):
    """Raised internally when verification cannot safely complete."""


@dataclass(slots=True)
class DefaultRootCauseAnalyzer:
    """Conservative classifier that never treats a missing cause as known."""

    async def analyze(self, failure: StageResult) -> RootCauseAnalysis:
        text = f"{failure.detail} {' '.join(failure.evidence)}".lower()
        classification = FailureClass.UNKNOWN
        keywords = {
            FailureClass.SYNTAX: ("syntax", "parseerror", "indentation"),
            FailureClass.TYPE: ("type", "mypy", "typing"),
            FailureClass.TEST: ("test", "assert", "pytest"),
            FailureClass.RUNTIME: ("runtime", "traceback", "exception"),
            FailureClass.DEPENDENCY: ("dependency", "importerror", "modulenotfound"),
            FailureClass.ARCHITECTURE: ("architecture", "coupling", "layer"),
            FailureClass.SECURITY: ("security", "permission", "vulnerability"),
            FailureClass.REQUIREMENT: ("requirement", "acceptance", "expected"),
            FailureClass.ENVIRONMENT: ("environment", "os", "platform", "configuration"),
        }
        for kind, terms in keywords.items():
            if any(term in text for term in terms):
                classification = kind
                break
        return RootCauseAnalysis(
            failure=failure.detail or "verification stage failed",
            classification=classification,
            suspected_cause=failure.detail or "cause could not be established",
            confidence=0.5 if classification is not FailureClass.UNKNOWN else 0.0,
            evidence=failure.evidence,
        )


@dataclass(slots=True)
class VerificationEngine:
    """Verify work independently and correct it only within a hard bound."""

    verifier: StageVerifier
    correction: CorrectionRunner
    root_cause: RootCauseAnalyzer | None = None
    regression: RegressionGuard | None = None
    limits: VerificationLimits = VerificationLimits()

    async def verify(self, request: VerificationRequest) -> VerificationReport:
        stages: list[StageResult] = []
        corrections: list[CorrectionRecord] = []
        failures: list[str] = []
        attempts = 0

        if self.regression is not None:
            baseline = await self.regression.verify_baseline(request)
            stages.append(baseline)
            if not baseline.passed:
                return self._escalate(
                    stages,
                    corrections,
                    failures + [baseline.detail],
                    "baseline regression verification failed",
                    attempts,
                )

        while True:
            current = await self._run_stages(request)
            stages.extend(current)
            failed = next((stage for stage in current if not stage.passed), None)
            if failed is None:
                if self.regression is not None:
                    regression = await self.regression.verify_regression(request)
                    stages.append(regression)
                    if not regression.passed:
                        failed = regression
                    else:
                        return VerificationReport(
                            "verified",
                            tuple(stages),
                            tuple(corrections),
                            tuple(failures),
                            attempts,
                            summary="All verification stages passed, including regression protection.",
                        )
                else:
                    return VerificationReport(
                        "verified",
                        tuple(stages),
                        tuple(corrections),
                        tuple(failures),
                        attempts,
                        summary="All independent verification stages passed.",
                    )

            failures.append(failed.detail or "verification stage failed")
            if attempts >= self.limits.max_correction_attempts:
                return self._escalate(
                    stages,
                    corrections,
                    failures,
                    "maximum correction attempts reached",
                    attempts,
                )

            attempts += 1
            analysis = await (self.root_cause or DefaultRootCauseAnalyzer()).analyze(failed)
            changes = await self.correction.correct(request, analysis)
            validation = await self._validate_correction(request)
            record = CorrectionRecord(
                attempts,
                failed.detail,
                analysis.classification,
                analysis.suspected_cause,
                changes,
                validation,
                analysis.evidence[0] if analysis.evidence else "uncertainty remains until full verification",
                analysis,
            )
            corrections.append(record)
            if validation != "validated":
                return self._escalate(
                    stages,
                    corrections,
                    failures,
                    "correction did not validate",
                    attempts,
                )

    async def _run_stages(self, request: VerificationRequest) -> tuple[StageResult, ...]:
        results = []
        for stage in VerificationStage:
            if stage is VerificationStage.REGRESSION and self.regression is not None:
                result = await self.regression.verify_regression(request)
            else:
                result = await self.verifier.verify(stage, request)
            results.append(result)
        return tuple(results)

    async def _validate_correction(self, request: VerificationRequest) -> str:
        result = await self.verifier.verify(VerificationStage.CODE, request)
        return "validated" if result.passed else "rejected"

    @staticmethod
    def _escalate(
        stages: list[StageResult],
        corrections: list[CorrectionRecord],
        failures: list[str],
        reason: str,
        attempts: int,
    ) -> VerificationReport:
        return VerificationReport(
            "escalated",
            tuple(stages),
            tuple(corrections),
            tuple(failures),
            attempts,
            True,
            reason,
            "Verification stopped without declaring success.",
        )
