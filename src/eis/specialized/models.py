"""Models for specialized EIS agents and multi-agent coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class AgentKind(StrEnum):
    RESEARCH = "research"
    PRODUCT = "product"
    ARCHITECTURE = "architecture"
    ENGINEERING = "engineering"
    TESTING = "testing"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True)
class AgentSpec:
    kind: AgentKind
    responsibility: str
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AgentAssignment:
    agent: AgentKind
    objective: str
    input: Any = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class AgentChallenge:
    challenger: AgentKind
    target: AgentKind
    claim: str
    evidence: tuple[str, ...] = ()
    accepted: bool = False


@dataclass(frozen=True, slots=True)
class CoordinationResult:
    assignments: tuple[AgentAssignment, ...]
    results: dict[AgentKind, Any]
    challenges: tuple[AgentChallenge, ...] = ()
    escalated: bool = False
    escalation_reason: str | None = None
