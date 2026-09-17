"""Protocols for independent verification and correction."""

from __future__ import annotations

from typing import Protocol

from eis.verification.models import (
    RootCauseAnalysis,
    StageResult,
    VerificationRequest,
    VerificationStage,
)


class StageVerifier(Protocol):
    async def verify(
        self, stage: VerificationStage, request: VerificationRequest
    ) -> StageResult: ...


class RootCauseAnalyzer(Protocol):
    async def analyze(self, failure: StageResult) -> RootCauseAnalysis: ...


class CorrectionRunner(Protocol):
    async def correct(
        self, request: VerificationRequest, analysis: RootCauseAnalysis
    ) -> tuple[str, ...]: ...


class RegressionGuard(Protocol):
    async def verify_baseline(self, request: VerificationRequest) -> StageResult: ...

    async def verify_regression(self, request: VerificationRequest) -> StageResult: ...
