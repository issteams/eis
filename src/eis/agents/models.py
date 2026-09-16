"""Provider-neutral models for the EIS agent runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class AgentState(StrEnum):
    RECEIVE = "receive"
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    OBSERVE = "observe"
    VERIFY = "verify"
    COMPLETE = "complete"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class AgentCapability:
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class AgentPermission:
    action: str
    resource: str


@dataclass(frozen=True, slots=True)
class Agent:
    id: UUID
    identity: str
    role: str
    capabilities: tuple[AgentCapability, ...] = ()
    permissions: tuple[AgentPermission, ...] = ()
    objectives: tuple[str, ...] = ()
    context: Any = None
    tools: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    execution_limits: dict[str, int] = field(default_factory=dict)
    memory: Any = None
    observability: Any = None

    @classmethod
    def create(
        cls,
        identity: str,
        role: str,
        *,
        capabilities: tuple[AgentCapability, ...] = (),
        permissions: tuple[AgentPermission, ...] = (),
        objectives: tuple[str, ...] = (),
        context: Any = None,
        tools: tuple[str, ...] = (),
        policies: tuple[str, ...] = (),
        execution_limits: dict[str, int] | None = None,
        memory: Any = None,
        observability: Any = None,
    ) -> Agent:
        return cls(
            uuid4(),
            identity,
            role,
            capabilities,
            permissions,
            objectives,
            context,
            tools,
            policies,
            execution_limits or {},
            memory,
            observability,
        )


@dataclass(frozen=True, slots=True)
class AgentTask:
    objective: str
    input: Any = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class AgentStep:
    name: str
    action: str
    resource: str | None = None
    input: Any = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class AgentPlan:
    steps: tuple[AgentStep, ...]


@dataclass(frozen=True, slots=True)
class AgentResult:
    state: AgentState
    output: Any = None
    error: str | None = None
    escalated: bool = False
    observations: tuple[Any, ...] = ()
