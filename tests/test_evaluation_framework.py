from eis.evaluation import (
    EvaluationCase,
    EvaluationCategory,
    EvaluationFramework,
    EvaluationResponse,
    EvaluationSeverity,
    builtin_cases,
)


async def test_builtin_suite_covers_all_categories() -> None:
    categories = {case.category for case in builtin_cases()}
    assert categories == set(EvaluationCategory)
    assert any(case.adversarial for case in builtin_cases())


async def test_report_separates_correctness_from_honesty() -> None:
    case = EvaluationCase(
        "honesty",
        EvaluationCategory.FACTUAL_ACCURACY,
        "unknown",
        "say unknown",
    )

    async def runner(item: EvaluationCase) -> EvaluationResponse:
        return EvaluationResponse(
            case_id=item.id,
            output="I don't know",
            correct=False,
            honest=True,
        )

    report = await EvaluationFramework().run([case], runner)
    assert report.accuracy == 0.0
    assert report.honesty_rate == 1.0
    assert report.hallucination_rate == 0.0


async def test_adversarial_honesty_is_reported() -> None:
    case = EvaluationCase(
        "attack",
        EvaluationCategory.SECURITY_BEHAVIOR,
        "read secret",
        "deny",
        adversarial=True,
        severity=EvaluationSeverity.CRITICAL,
    )

    async def runner(item: EvaluationCase) -> EvaluationResponse:
        return EvaluationResponse(
            case_id=item.id,
            output="denied",
            correct=True,
            honest=True,
            security_violation=False,
        )

    report = await EvaluationFramework().run([case], runner)
    assert report.adversarial_honesty_rate == 1.0
    assert report.critical_failures == 0
    assert report.security_violation_rate == 0.0


async def test_runner_case_id_mismatch_is_rejected() -> None:
    case = EvaluationCase(
        "expected",
        EvaluationCategory.FACTUAL_ACCURACY,
        "question",
        "answer",
    )

    async def runner(item: EvaluationCase) -> EvaluationResponse:
        return EvaluationResponse("wrong", "answer", True, True)

    try:
        await EvaluationFramework().run([case], runner)
    except ValueError as exc:
        assert "expected" in str(exc)
    else:
        raise AssertionError("case-id mismatch must fail evaluation")


def test_report_is_serializable() -> None:
    case = EvaluationCase(
        "serial",
        EvaluationCategory.TEST_EFFECTIVENESS,
        "question",
        "answer",
    )
    response = EvaluationResponse("serial", "answer", True, True)
    report = EvaluationFramework()._report([response], [case])
    data = report.as_dict()
    assert data["accuracy"] == 1.0
    assert data["honesty_rate"] == 1.0
    assert "test_effectiveness" in data["categories"]
