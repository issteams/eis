"""Protocols for controlled EIS agent execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from eis.agents.models import Agent, AgentPlan, AgentResult, AgentStep, AgentTask


class Planner(Protocol):
    def plan(self, agent: Agent, task: AgentTask) -> AgentPlan: ...


class Tool(Protocol):
    name: str

    def invoke(self, step: AgentStep) -> Awaitable[Any]: ...


class Policy(Protocol):
    def allow(self, agent: Agent, step: AgentStep) -> bool: ...


class Observer(Protocol):
    def observe(self, event: str, data: Any) -> None: ...


EscalationHandler = Callable[[Agent, AgentTask, Exception], Awaitable[AgentResult]]
