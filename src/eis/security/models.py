"""Security, governance, and audit models for EIS."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    DEPLOY = "deploy"
    DATABASE = "database"
    CREDENTIAL = "credential"
    COMMUNICATION = "communication"
    FINANCIAL = "financial"
    EXECUTE = "execute"


class AuthorizationStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"
    UNKNOWN = "unknown"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class Principal:
    id: str
    roles: frozenset[str] = frozenset()
    authenticated: bool = True


@dataclass(frozen=True, slots=True)
class Permission:
    action: str
    resource: str


@dataclass(frozen=True, slots=True)
class Role:
    name: str
    permissions: frozenset[Permission] = frozenset()


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    id: UUID
    role: str
    permissions: frozenset[Permission] = frozenset()


@dataclass(frozen=True, slots=True)
class ResourceRestriction:
    resource: str
    allowed_actions: frozenset[str]


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    principal: Principal
    action: str
    resource: str
    risk_level: RiskLevel = RiskLevel.LOW
    agent: AgentIdentity | None = None
    tool: str | None = None
    task_id: UUID | None = None
    target: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    status: AuthorizationStatus
    reason: str
    approval_required: bool = False


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    action: str
    resource: str
    actor: str
    reason: str
    risk_level: RiskLevel
    task_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class Approval:
    request_id: UUID
    status: ApprovalStatus
    approver: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AuditRecord:
    actor: str
    agent: str | None
    task: str | None
    action: str
    tool: str | None
    target: str | None
    timestamp: str
    result: str
    risk_level: RiskLevel
    authorization: AuthorizationStatus
    failure: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class GovernanceLimits:
    max_actions_per_window: int = 60
    window_seconds: float = 60.0
    max_cost: float = 100.0
    max_execution_seconds: float = 600.0


@dataclass(frozen=True, slots=True)
class ActionRequest:
    actor: Principal
    action: ActionType | str
    resource: str
    risk_level: RiskLevel = RiskLevel.LOW
    tool: str | None = None
    target: str | None = None
    task_id: UUID | None = None
    agent: AgentIdentity | None = None
    estimated_cost: float = 0.0
    estimated_seconds: float = 0.0
    input_data: Any = None
