import asyncio

from eis.verification import (
    FailureClass,
    RootCauseAnalysis,
    StageResult,
    VerificationEngine,
    VerificationLimits,
    VerificationRequest,
    VerificationStage,
)


class FixtureVerifier:
    def __init__(self, failing_stage=None):
        self.failing_stage = failing_stage
        self.calls = []
        self.fail_once = failing_stage is not None

    async def verify(self, stage, request):
        self.calls.append(stage)
        if stage is self.failing_stage and self.fail_once:
            self.fail_once = False
            return StageResult(stage, False, "test assertion failed", ("assertion",))
        return StageResult(stage, True, "passed")


class AlwaysFailVerifier:
    def __init__(self, failing_stage):
        self.failing_stage = failing_stage
        self.calls = []

    async def verify(self, stage, request):
        self.calls.append(stage)
        if stage is self.failing_stage:
            return StageResult(stage, False, "security verification failed")
        return StageResult(stage, True, "passed")


class FixtureCorrection:
    def __init__(self):
        self.calls = []

    async def correct(self, request, analysis):
        self.calls.append(analysis)
        return ("fixture.py",)


class FixtureRegression:
    def __init__(self):
        self.baseline_calls = 0
        self.regression_calls = 0

    async def verify_baseline(self, request):
        self.baseline_calls += 1
        return StageResult(VerificationStage.REGRESSION, True, "baseline passed")

    async def verify_regression(self, request):
        self.regression_calls += 1
        return StageResult(VerificationStage.REGRESSION, True, "regression passed")


class FixtureRootCause:
    async def analyze(self, failure):
        return RootCauseAnalysis(
            failure.detail,
            FailureClass.TEST,
            "fixture assertion is stale",
            0.9,
            ("assertion",),
        )


def request():
    return VerificationRequest("add feature", "/fixture", ("fixture.py",))


def test_verifier_requires_all_independent_stages():
    verifier = FixtureVerifier()
    engine = VerificationEngine(verifier, FixtureCorrection())

    report = asyncio.run(engine.verify(request()))

    assert report.verified
    assert [result.stage for result in report.stages] == list(VerificationStage)
    assert report.attempts == 0


def test_failed_verification_is_classified_corrected_and_retested():
    verifier = FixtureVerifier(VerificationStage.TEST)
    correction = FixtureCorrection()
    engine = VerificationEngine(
        verifier,
        correction,
        root_cause=FixtureRootCause(),
        limits=VerificationLimits(max_correction_attempts=2),
    )

    report = asyncio.run(engine.verify(request()))

    assert report.verified
    assert report.attempts == 1
    assert len(report.corrections) == 1
    assert report.corrections[0].original_failure == "test assertion failed"
    assert report.corrections[0].classification is FailureClass.TEST
    assert correction.calls
    assert verifier.calls.count(VerificationStage.TEST) == 2


def test_correction_limit_escalates_without_false_success():
    verifier = AlwaysFailVerifier(VerificationStage.SECURITY)
    correction = FixtureCorrection()
    engine = VerificationEngine(
        verifier,
        correction,
        limits=VerificationLimits(max_correction_attempts=1),
    )

    report = asyncio.run(engine.verify(request()))

    assert report.escalated
    assert not report.verified
    assert report.attempts == 1
    assert report.escalation_reason == "maximum correction attempts reached"
    assert len(report.corrections) == 1


def test_regression_is_checked_before_and_after_correction():
    verifier = FixtureVerifier(VerificationStage.CODE)
    regression = FixtureRegression()
    engine = VerificationEngine(
        verifier,
        FixtureCorrection(),
        regression=regression,
        limits=VerificationLimits(max_correction_attempts=1),
    )

    report = asyncio.run(engine.verify(request()))

    assert report.verified
    assert regression.baseline_calls == 1
    assert regression.regression_calls == 1
