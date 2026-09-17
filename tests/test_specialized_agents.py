import asyncio

from eis.specialized import (
    SPECS,
    AgentAssignment,
    AgentKind,
    AgentOrchestrator,
    DefaultAgentFactory,
)


class FixtureRunner:
    def __init__(self):
        self.calls = []
        self.challenges = []

    async def __call__(self, kind, objective, input):
        self.calls.append((kind, objective, input))
        return {"agent": kind.value, "objective": objective}

    async def challenge(self, challenger, target, result):
        from eis.specialized import AgentChallenge

        challenge = AgentChallenge(challenger, target, f"review {target.value}", ("fixture",))
        self.challenges.append(challenge)
        return challenge


def test_all_specialists_have_explicit_contracts():
    assert set(SPECS) == set(AgentKind)
    for spec in SPECS.values():
        assert spec.responsibility
        assert spec.capabilities
        assert spec.permissions
        assert spec.inputs
        assert spec.outputs
        assert spec.limitations


def test_orchestrator_coordinates_agents_and_preserves_challenges():
    runner = FixtureRunner()
    orchestrator = AgentOrchestrator(DefaultAgentFactory(runner))
    assignments = (
        AgentAssignment(AgentKind.PRODUCT, "propose feature"),
        AgentAssignment(AgentKind.ARCHITECTURE, "review feature"),
        AgentAssignment(AgentKind.SECURITY, "assess feature"),
    )

    result = asyncio.run(orchestrator.run(assignments))

    assert set(result.results) == {
        AgentKind.PRODUCT,
        AgentKind.ARCHITECTURE,
        AgentKind.SECURITY,
    }
    assert len(result.challenges) == 6
    assert len(runner.calls) == 3


def test_orchestrator_has_hard_assignment_limit():
    runner = FixtureRunner()
    orchestrator = AgentOrchestrator(DefaultAgentFactory(runner), max_assignments=1)

    result = asyncio.run(
        orchestrator.run(
            (
                AgentAssignment(AgentKind.RESEARCH, "one"),
                AgentAssignment(AgentKind.ANALYSIS, "two"),
            )
        )
    )

    assert result.escalated
    assert not runner.calls
