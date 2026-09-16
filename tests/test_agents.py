import asyncio

from eis.agents import (
    Agent,
    AgentPermission,
    AgentPlan,
    AgentResult,
    AgentRuntime,
    AgentState,
    AgentStep,
    AgentTask,
    PermissionDeniedError,
)


class Planner:
    def __init__(self, plan):
        self.plan_value = plan

    def plan(self, agent, task):
        return self.plan_value


class Tool:
    name = "echo"

    async def invoke(self, step):
        return step.input


class DenyPolicy:
    def allow(self, agent, step):
        return False


class Observer:
    def __init__(self):
        self.events = []

    def observe(self, event, data):
        self.events.append(event)


def test_agent_lifecycle_and_tool_execution():
    step = AgentStep("echo", "echo", "test", "ok")
    agent = Agent.create("test-agent", "tester", permissions=(AgentPermission("echo", "test"),))
    observer = Observer()
    runtime = AgentRuntime(Planner(AgentPlan((step,))), {"echo": Tool()}, observer=observer)

    result = asyncio.run(runtime.run(agent, AgentTask("echo")))

    assert result.state is AgentState.COMPLETE
    assert result.output == "ok"
    assert observer.events == [
        "receive", "understand", "plan", "execute", "observe", "verify", "complete"
    ]


def test_permission_boundary_escalates_without_permission():
    step = AgentStep("echo", "echo", "test", "blocked")
    agent = Agent.create("test-agent", "tester")
    runtime = AgentRuntime(Planner(AgentPlan((step,))), {"echo": Tool()})

    result = asyncio.run(runtime.run(agent, AgentTask("echo")))

    assert result.state is AgentState.ESCALATE
    assert result.escalated
    assert "permission denied" in result.error


def test_policy_boundary_escalates():
    step = AgentStep("echo", "echo", "test", "blocked")
    agent = Agent.create("test-agent", "tester", permissions=(AgentPermission("echo", "test"),))
    runtime = AgentRuntime(Planner(AgentPlan((step,))), {"echo": Tool()}, policies=(DenyPolicy(),))

    result = asyncio.run(runtime.run(agent, AgentTask("echo")))

    assert result.state is AgentState.ESCALATE
    assert result.escalated
    assert "policy denied" in result.error
