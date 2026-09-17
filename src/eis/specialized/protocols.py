"""Protocols for reusable specialized-agent implementations."""

from __future__ import annotations

from typing import Any, Protocol

from eis.specialized.models import AgentChallenge, AgentKind, AgentSpec


class SpecializedAgent(Protocol):
    spec: AgentSpec

    async def run(self, objective: str, input: Any = None) -> Any: ...

    async def challenge(self, target: AgentKind, result: Any) -> AgentChallenge | None: ...


class AgentFactory(Protocol):
    def create(self, kind: AgentKind) -> SpecializedAgent: ...
