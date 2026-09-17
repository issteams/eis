"""Evaluation execution and measurable scoring."""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from uuid import uuid4

from eis.evaluation.models import (
    CategoryScore,
    EvaluationCase,
    EvaluationCategory,
    EvaluationReport,
    EvaluationResponse,
    EvaluationSeverity,
)
from eis.evaluation.protocols import EvaluationRunner


class EvaluationFramework:
    """Run benchmark cases and score correctness and honesty independently."""

    async def run(
        self,
        cases: Iterable[EvaluationCase],
        runner: EvaluationRunner,
    ) -> EvaluationReport:
        """Execute all cases and produce a report.

        A case is never considered honest merely because it completed. The runner
        must explicitly report correctness, honesty, and relevant safety signals.
        """
        case_list = tuple(cases)
        responses: list[EvaluationResponse] = []
        for case in case_list:
            response = runner(case)
            if inspect.isawaitable(response):
                response = await response
            if response.case_id != case.id:
                raise ValueError(f"runner returned case {response.case_id!r} for {case.id!r}")
            responses.append(response)

        return self._report(responses, case_list)

    def _report(
        self,
        responses: list[EvaluationResponse],
        cases: Iterable[EvaluationCase],
    ) -> EvaluationReport:
        case_map = {case.id: case for case in cases}
        scores: list[CategoryScore] = []
        for category in EvaluationCategory:
            category_cases = [
                response for response in responses if case_map[response.case_id].category is category
            ]
            adversarial = [
                response for response in category_cases if case_map[response.case_id].adversarial
            ]
            critical_failures = sum(
                1
                for response in category_cases
                if not response.correct
                and case_map[response.case_id].severity is EvaluationSeverity.CRITICAL
            )
            scores.append(
                CategoryScore(
                    category=category,
                    cases=len(category_cases),
                    correct=sum(response.correct for response in category_cases),
                    honest=sum(response.honest for response in category_cases),
                    adversarial_cases=len(adversarial),
                    adversarial_honest=sum(response.honest for response in adversarial),
                    failures=sum(not response.correct for response in category_cases),
                    critical_failures=critical_failures,
                )
            )

        return EvaluationReport(
            run_id=str(uuid4()),
            total_cases=len(responses),
            correct=sum(response.correct for response in responses),
            honest=sum(response.honest for response in responses),
            adversarial_cases=sum(
                case_map[response.case_id].adversarial for response in responses
            ),
            adversarial_honest=sum(
                response.honest for response in responses if case_map[response.case_id].adversarial
            ),
            hallucinations=sum(response.hallucinated for response in responses),
            security_violations=sum(response.security_violation for response in responses),
            permission_violations=sum(response.permission_violation for response in responses),
            critical_failures=sum(
                not response.correct
                and case_map[response.case_id].severity is EvaluationSeverity.CRITICAL
                for response in responses
            ),
            category_scores=tuple(scores),
            responses=tuple(responses),
        )


__all__ = ["EvaluationFramework"]
