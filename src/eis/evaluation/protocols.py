"""Protocols for running and judging EIS evaluation cases."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from eis.evaluation.models import EvaluationCase, EvaluationResponse


EvaluationRunner = Callable[[EvaluationCase], EvaluationResponse | Awaitable[EvaluationResponse]]


class CaseJudge(Protocol):
    """Judge an observed response against an evaluation case."""

    def judge(self, case: EvaluationCase, output: str) -> EvaluationResponse: ...


class EvaluationRunnerProtocol(Protocol):
    """Execute one evaluation case."""

    def run(
        self, case: EvaluationCase
    ) -> EvaluationResponse | Awaitable[EvaluationResponse]: ...


class EvaluationSuite(Protocol):
    """Provide the cases belonging to an evaluation suite."""

    def cases(self) -> Sequence[EvaluationCase]: ...


__all__ = ["CaseJudge", "EvaluationRunner", "EvaluationRunnerProtocol", "EvaluationSuite"]
