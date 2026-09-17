"""Provider-independent security and governance protocols."""

from __future__ import annotations

from typing import Protocol

from eis.security.models import (
    ActionRequest,
    Approval,
    ApprovalRequest,
    AuditRecord,
    AuthorizationDecision,
    AuthorizationRequest,
    Principal,
)


class Authenticator(Protocol):
    def authenticate(self, credential: str) -> Principal | None: ...


class Authorizer(Protocol):
    def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision: ...


class ApprovalGate(Protocol):
    def request(self, request: ApprovalRequest) -> Approval: ...

    def resolve(
        self,
        approval: Approval,
        *,
        approver: str,
        approved: bool,
        reason: str,
    ) -> Approval: ...


class AuditSink(Protocol):
    def record(self, record: AuditRecord) -> None: ...


class SecretProvider(Protocol):
    def get(self, name: str) -> str | None: ...


class SensitiveDataProtector(Protocol):
    def redact(self, value: object) -> object: ...


class GovernanceGuard(Protocol):
    def check(self, request: ActionRequest) -> None: ...

    def commit(self, request: ActionRequest, actual_cost: float, actual_seconds: float) -> None: ...


__all__ = [
    "ApprovalGate",
    "AuditSink",
    "Authenticator",
    "Authorizer",
    "GovernanceGuard",
    "SecretProvider",
    "SensitiveDataProtector",
]
