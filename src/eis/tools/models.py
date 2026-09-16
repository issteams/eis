"""Models for the secure EIS tool and execution system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class ExecutionPolicy(StrEnum):
    READ_ONLY = "read_only"
    SAFE_WRITE = "safe_write"
    CONTROLLED_WRITE = "controlled_write"
    HIGH_RISK = "high_risk"
    PROHIBITED = "prohibited"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    DENIED = "denied"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class ToolSchema:
    schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: ToolSchema
    output_schema: ToolSchema
    permissions: tuple[str, ...] = ()
    risk_level: RiskLevel = RiskLevel.LOW
    timeout_seconds: float = 30.0
    execution_policy: ExecutionPolicy = ExecutionPolicy.READ_ONLY
    audit_category: str = "tool"


@dataclass(frozen=True, slots=True)
class ToolRequest:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    granted_permissions: frozenset[str] = frozenset()
    agent_id: UUID | None = None
    task_id: UUID | None = None
    request_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class ToolResult:
    status: ExecutionStatus
    output: Any = None
    error: str | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    request_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AuditEvent:
    request_id: UUID
    tool: str
    status: ExecutionStatus
    policy: ExecutionPolicy
    risk_level: RiskLevel
    agent_id: UUID | None = None
    task_id: UUID | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0
