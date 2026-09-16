"""Controlled, provider-neutral EIS agent runtime."""

from __future__ import annotations

from eis.agents.models import (
    Agent,
    AgentPermission,
    AgentResult,
    AgentState,
    AgentTask,
)
from eis.agents.protocols import EscalationHandler, Observer, Planner, Policy, Tool


class PermissionDeniedError(RuntimeError):
    """Raised when a tool invocation is outside the agent permission boundary."""


class AgentRuntime:
    """Execute planned steps through explicit permission and policy gates."""

    def __init__(
        self,
        planner: Planner,
        tools: dict[str, Tool],
        policies: tuple[Policy, ...] = (),
        observer: Observer | None = None,
        escalation: EscalationHandler | None = None,
    ) -> None:
        self._planner = planner
        self._tools = tools
        self._policies = policies
        self._observer = observer
        self._escalation = escalation

    async def run(self, agent: Agent, task: AgentTask) -> AgentResult:
        observations: list[object] = []
        try:
            await self._emit(AgentState.RECEIVE.value, task)
            await self._emit(AgentState.UNDERSTAND.value, task)
            plan = self._planner.plan(agent, task)
            await self._emit(AgentState.PLAN.value, plan)
            output = None
            for step in plan.steps:
                await self._emit(AgentState.EXECUTE.value, step)
                tool = self._tools.get(step.action)
                if tool is None:
                    raise PermissionDeniedError(f"tool is not registered: {step.action}")
                self._authorize(agent, step)
                output = await tool.invoke(step)
                observations.append(output)
                await self._emit(AgentState.OBSERVE.value, output)
            await self._emit(AgentState.VERIFY.value, output)
            await self._emit(AgentState.COMPLETE.value, output)
            return AgentResult(AgentState.COMPLETE, output, observations=tuple(observations))
        except Exception as exc:
            await self._emit(AgentState.ESCALATE.value, str(exc))
            if self._escalation is not None:
                return await self._escalation(agent, task, exc)
            return AgentResult(
                AgentState.ESCALATE,
                error=str(exc),
                escalated=True,
                observations=tuple(observations),
            )

    def _authorize(self, agent: Agent, step: object) -> None:
        action = getattr(step, "action")
        resource = getattr(step, "resource")
        permission = AgentPermission(action, resource or "*")
        allowed = permission in agent.permissions or AgentPermission(action, "*") in agent.permissions
        if not allowed:
            raise PermissionDeniedError(f"permission denied: {action}:{resource}")
        for policy in self._policies:
            if not policy.allow(agent, step):
                raise PermissionDeniedError(f"policy denied: {action}:{resource}")

    async def _emit(self, event: str, data: object) -> None:
        if self._observer is not None:
            self._observer.observe(event, data)
