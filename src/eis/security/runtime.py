"""Fail-closed security, approval, audit, and governance runtime."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from fnmatch import fnmatch
from threading import Lock

from eis.security.models import (
    ActionRequest,
    Approval,
    ApprovalRequest,
    ApprovalStatus,
    AuditRecord,
    AuthorizationDecision,
    AuthorizationRequest,
    AuthorizationStatus,
    GovernanceLimits,
    Permission,
    Principal,
    ResourceRestriction,
    Role,
    RiskLevel,
)


class SecurityError(PermissionError):
    """Base error for security-boundary failures."""


class AuthorizationError(SecurityError):
    """Raised when an action cannot be authorized."""


class GovernanceLimitError(SecurityError):
    """Raised when a governance limit is exceeded."""


@dataclass(frozen=True, slots=True)
class TokenAuthenticator:
    """Minimal credential interface implementation for integration tests.

    Production deployments should replace this with an identity-provider adapter;
    credentials are never persisted by this class.
    """

    credentials: dict[str, str] = field(default_factory=dict)

    def authenticate(self, credential: str) -> Principal | None:
        digest = hashlib.sha256(credential.encode()).hexdigest()
        principal_id = self.credentials.get(digest)
        return Principal(principal_id) if principal_id is not None else None


@dataclass(slots=True)
class RoleAuthorizer:
    """RBAC authorizer that fails closed for unknown principals, roles, or resources."""

    roles: dict[str, Role] = field(default_factory=dict)
    principals: dict[str, Principal] = field(default_factory=dict)
    restrictions: tuple[ResourceRestriction, ...] = ()

    def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision:
        if not request.principal.authenticated:
            return AuthorizationDecision(AuthorizationStatus.DENIED, "principal is not authenticated")
        principal = self.principals.get(request.principal.id, request.principal)
        permissions: set[Permission] = set()
        for role_name in principal.roles:
            role = self.roles.get(role_name)
            if role is None:
                return AuthorizationDecision(AuthorizationStatus.DENIED, f"unknown role: {role_name}")
            permissions.update(role.permissions)
        if request.agent is not None:
            permissions.update(request.agent.permissions)
        if not any(
            permission.action == request.action
            and fnmatch(request.resource, permission.resource)
            for permission in permissions
        ):
            return AuthorizationDecision(AuthorizationStatus.DENIED, "permission not granted")
        for restriction in self.restrictions:
            if fnmatch(request.resource, restriction.resource) and request.action not in restriction.allowed_actions:
                return AuthorizationDecision(AuthorizationStatus.DENIED, "resource restriction denied")
        return AuthorizationDecision(AuthorizationStatus.ALLOWED, "authorized")

    def allowed(self, principal: str, action: str, resource: str) -> bool:
        identity = self.principals.get(principal)
        if identity is None:
            return False
        return self.authorize(AuthorizationRequest(identity, action, resource)).status is AuthorizationStatus.ALLOWED


@dataclass(slots=True)
class InMemoryApprovalGate:
    approvals: dict[str, Approval] = field(default_factory=dict)

    def request(self, request: ApprovalRequest) -> Approval:
        approval = Approval(request.id, ApprovalStatus.PENDING)
        self.approvals[str(request.id)] = approval
        return approval

    def resolve(self, approval: Approval, *, approver: str, approved: bool, reason: str) -> Approval:
        if not approver.strip() or not reason.strip():
            raise AuthorizationError("approval requires an identified approver and reason")
        updated = Approval(
            approval.request_id,
            ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED,
            approver,
            reason,
        )
        self.approvals[str(approval.request_id)] = updated
        return updated


@dataclass(slots=True)
class InMemoryAuditSink:
    records: list[AuditRecord] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def record(self, record: AuditRecord) -> None:
        with self._lock:
            self.records.append(record)


_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|authorization)\s*[:=]\s*[^,\s]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"),
)


@dataclass(frozen=True, slots=True)
class RedactingProtector:
    """Redact common credential-bearing strings before audit or telemetry storage."""

    replacement: str = "[REDACTED]"

    def redact(self, value: object) -> object:
        if isinstance(value, str):
            result = value
            for pattern in _SECRET_PATTERNS:
                result = pattern.sub(self.replacement, result)
            return result
        if isinstance(value, dict):
            return {str(key): self.redact(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self.redact(item) for item in value)
        return value


@dataclass(slots=True)
class GovernanceGuard:
    """Enforce action rate, cost, and execution budgets with fail-closed behavior."""

    limits: GovernanceLimits = field(default_factory=GovernanceLimits)
    _actions: list[float] = field(default_factory=list)
    _cost: float = 0.0
    _execution_seconds: float = 0.0

    def check(self, request: ActionRequest) -> None:
        now = time.monotonic()
        self._actions = [stamp for stamp in self._actions if now - stamp <= self.limits.window_seconds]
        if len(self._actions) >= self.limits.max_actions_per_window:
            raise GovernanceLimitError("action rate limit exceeded")
        if request.estimated_cost < 0 or self._cost + request.estimated_cost > self.limits.max_cost:
            raise GovernanceLimitError("cost limit exceeded")
        if request.estimated_seconds < 0 or self._execution_seconds + request.estimated_seconds > self.limits.max_execution_seconds:
            raise GovernanceLimitError("execution limit exceeded")

    def commit(self, request: ActionRequest, actual_cost: float, actual_seconds: float) -> None:
        if actual_cost < 0 or actual_seconds < 0:
            raise GovernanceLimitError("negative usage is invalid")
        self._actions.append(time.monotonic())
        self._cost += actual_cost
        self._execution_seconds += actual_seconds


HIGH_RISK_ACTIONS = frozenset(
    {
        "production_deploy",
        "destructive_database",
        "delete_repository",
        "delete_file",
        "credential_change",
        "external_communication",
        "financial_action",
    }
)


@dataclass(slots=True)
class SecurityGateway:
    """Single action boundary combining authorization, governance, approvals, and audit."""

    authorizer: RoleAuthorizer
    audit: InMemoryAuditSink
    approval_gate: InMemoryApprovalGate = field(default_factory=InMemoryApprovalGate)
    governance: GovernanceGuard = field(default_factory=GovernanceGuard)
    protector: RedactingProtector = field(default_factory=RedactingProtector)

    def authorize(self, request: ActionRequest) -> AuthorizationDecision:
        if request.action in HIGH_RISK_ACTIONS or request.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return AuthorizationDecision(
                AuthorizationStatus.APPROVAL_REQUIRED,
                "human approval required for high-risk action",
                approval_required=True,
            )
        return self.authorizer.authorize(
            AuthorizationRequest(
                request.actor,
                str(request.action),
                request.resource,
                request.risk_level,
                request.agent,
                request.tool,
                request.task_id,
                request.target,
            )
        )

    def check(self, request: ActionRequest) -> AuthorizationDecision:
        decision = self.authorize(request)
        if decision.status is not AuthorizationStatus.ALLOWED:
            self._audit(request, decision, "denied", decision.reason)
            raise AuthorizationError(decision.reason)
        self.governance.check(request)
        return decision

    def execute_approved(
        self,
        request: ActionRequest,
        *,
        approval: Approval | None = None,
        result: str = "success",
        failure: str | None = None,
        actual_cost: float = 0.0,
        actual_seconds: float = 0.0,
    ) -> None:
        decision = self.authorize(request)
        if decision.status is AuthorizationStatus.APPROVAL_REQUIRED:
            if approval is None or approval.status is not ApprovalStatus.APPROVED:
                self._audit(request, decision, "approval_required", "valid human approval missing")
                raise AuthorizationError("valid human approval required")
        elif decision.status is not AuthorizationStatus.ALLOWED:
            self._audit(request, decision, "denied", decision.reason)
            raise AuthorizationError(decision.reason)
        self.governance.check(request)
        self.governance.commit(request, actual_cost, actual_seconds)
        self._audit(request, AuthorizationDecision(AuthorizationStatus.ALLOWED, "authorized"), result, failure)

    def _audit(
        self,
        request: ActionRequest,
        decision: AuthorizationDecision,
        result: str,
        failure: str | None,
    ) -> None:
        self.audit.record(
            AuditRecord(
                actor=request.actor.id,
                agent=str(request.agent.id) if request.agent is not None else None,
                task=str(request.task_id) if request.task_id is not None else None,
                action=str(request.action),
                tool=request.tool,
                target=str(self.protector.redact(request.target)),
                timestamp=datetime.now(UTC).isoformat(),
                result=result,
                risk_level=request.risk_level,
                authorization=decision.status,
                failure=self.protector.redact(failure),
                metadata={"resource": self.protector.redact(request.resource)},
            )
        )
