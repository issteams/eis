"""Shared specialized-agent runtime and coordination orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eis.specialized.models import (
    AgentAssignment,
    AgentChallenge,
    AgentKind,
    AgentSpec,
    CoordinationResult,
)
from eis.specialized.protocols import AgentFactory, SpecializedAgent


SPECS: dict[AgentKind, AgentSpec] = {
    AgentKind.RESEARCH: AgentSpec(
        AgentKind.RESEARCH,
        "Find and synthesize evidence.",
        ("research", "source evaluation"),
        ("context.read", "knowledge.read"),
        ("objective", "context"),
        ("findings", "evidence"),
        ("does not implement or modify projects",),
    ),
    AgentKind.PRODUCT: AgentSpec(
        AgentKind.PRODUCT,
        "Define product requirements and trade-offs.",
        ("requirements", "prioritization"),
        ("context.read", "knowledge.read"),
        ("problem", "research"),
        ("proposal", "requirements"),
        ("does not implement code",),
    ),
    AgentKind.ARCHITECTURE: AgentSpec(
        AgentKind.ARCHITECTURE,
        "Evaluate system design and integration boundaries.",
        ("architecture review", "dependency analysis"),
        ("repository.read", "context.read"),
        ("proposal", "repository"),
        ("architecture assessment", "challenges"),
        ("does not modify production code",),
    ),
    AgentKind.ENGINEERING: AgentSpec(
        AgentKind.ENGINEERING,
        "Implement approved software changes.",
        ("implementation", "debugging"),
        ("repository.read", "controlled.write", "test.execute"),
        ("plan", "repository", "architecture"),
        ("changes", "implementation report"),
        ("bounded by execution and modification limits",),
    ),
    AgentKind.TESTING: AgentSpec(
        AgentKind.TESTING,
        "Validate behavior and detect regressions.",
        ("test design", "regression analysis"),
        ("repository.read", "test.execute"),
        ("requirements", "changes"),
        ("test results", "defects"),
        ("does not silently patch failures",),
    ),
    AgentKind.SECURITY: AgentSpec(
        AgentKind.SECURITY,
        "Identify security risks and unsafe changes.",
        ("threat analysis", "security review"),
        ("repository.read", "context.read"),
        ("design", "changes"),
        ("security assessment", "challenges"),
        ("does not approve unverified risk",),
    ),
    AgentKind.DOCUMENTATION: AgentSpec(
        AgentKind.DOCUMENTATION,
        "Produce accurate project documentation.",
        ("technical writing", "documentation analysis"),
        ("repository.read", "controlled.write"),
        ("implementation", "architecture"),
        ("documentation changes",),
        ("must not invent undocumented behavior",),
    ),
    AgentKind.ANALYSIS: AgentSpec(
        AgentKind.ANALYSIS,
        "Compare evidence and identify unresolved issues.",
        ("synthesis", "trade-off analysis"),
        ("context.read", "knowledge.read"),
        ("agent findings", "evidence"),
        ("analysis", "uncertainties"),
        ("does not substitute analysis for verification",),
    ),
}


@dataclass(slots=True)
class GenericSpecializedAgent:
    spec: AgentSpec
    runner: Any

    async def run(self, objective: str, input: Any = None) -> Any:
        return await self.runner(self.spec.kind, objective, input)

    async def challenge(self, target: AgentKind, result: Any) -> AgentChallenge | None:
        challenge = None
        if hasattr(self.runner, "challenge"):
            challenge = await self.runner.challenge(self.spec.kind, target, result)
        return challenge


class DefaultAgentFactory:
    """Builds all specialties over the same shared runner."""

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def create(self, kind: AgentKind) -> SpecializedAgent:
        return GenericSpecializedAgent(SPECS[kind], self._runner)


class AgentOrchestrator:
    """Assign work, collect independent outputs, and preserve challenges."""

    def __init__(self, factory: AgentFactory, *, max_assignments: int = 16) -> None:
        if max_assignments < 1:
            raise ValueError("max_assignments must be positive")
        self._factory = factory
        self._max_assignments = max_assignments

    async def run(self, assignments: tuple[AgentAssignment, ...]) -> CoordinationResult:
        if len(assignments) > self._max_assignments:
            return CoordinationResult(
                assignments,
                {},
                escalated=True,
                escalation_reason="maximum assignments exceeded",
            )
        results: dict[AgentKind, Any] = {}
        challenges: list[AgentChallenge] = []
        for assignment in assignments:
            agent = self._factory.create(assignment.agent)
            results[assignment.agent] = await agent.run(assignment.objective, assignment.input)

        for assignment in assignments:
            agent = self._factory.create(assignment.agent)
            for target, result in results.items():
                if target is assignment.agent:
                    continue
                challenge = await agent.challenge(target, result)
                if challenge is not None:
                    challenges.append(challenge)
        return CoordinationResult(assignments, results, tuple(challenges))
