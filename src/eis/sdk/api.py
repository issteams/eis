"""Stable, typed public facade for EIS.

Only this module and :mod:`eis.sdk.models` are intended as the supported SDK
surface. Runtime modules remain implementation details.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from eis.sdk.models import (
    AgentResult,
    AuditEntry,
    EngineeringResult,
    EvaluationResult,
    ExecutionResult,
    KnowledgeItem,
    Product,
    Task,
    TaskResult,
    TaskStatus,
    WorkflowResult,
)

AgentHandler = Callable[[Task], Any]
EvaluatorHandler = Callable[[str], EvaluationResult | Awaitable[EvaluationResult]]
EngineeringHandler = Callable[[Task], Any]
ToolHandler = Callable[[dict[str, Any]], Any]
WorkflowHandler = Callable[[Task], Any]


class Agent(Protocol):
    """Public agent contract accepted by :class:`EIS`."""

    name: str

    def run(self, task: Task) -> Any: ...


class Evaluator(Protocol):
    """Public idea-evaluation contract."""

    def evaluate(self, subject: str) -> EvaluationResult | Awaitable[EvaluationResult]: ...


class Engineer(Protocol):
    """Public engineering execution contract."""

    def execute(self, task: Task) -> Any: ...


class Tool(Protocol):
    """Public tool contract; security remains the application's responsibility."""

    name: str

    def execute(self, arguments: dict[str, Any]) -> Any: ...


class Executor(Protocol):
    """Public execution contract for application-owned executors."""

    def execute(self, action: str, arguments: dict[str, Any]) -> Any: ...


class Orchestrator(Protocol):
    """Public workflow orchestration contract."""

    def run(self, workflow: str, task: Task) -> Any: ...


@dataclass(slots=True)
class _RegisteredAgent:
    name: str
    handler: AgentHandler


@dataclass(slots=True)
class _Memory:
    items: list[str] = field(default_factory=list)


class EIS:
    """Primary entry point for the EIS Python SDK.

    The facade owns user-facing state and delegates advanced behavior to
    explicitly supplied adapters. No provider, database, model, or runtime
    implementation is selected implicitly.
    """

    def __init__(self, *, name: str = "Echowavs Intelligence System") -> None:
        self.name = name
        self._products: dict[UUID, Product] = {}
        self._knowledge: dict[UUID, KnowledgeItem] = {}
        self._tasks: dict[UUID, TaskResult] = {}
        self._agents: dict[str, _RegisteredAgent] = {}
        self._tools: dict[str, ToolHandler] = {}
        self._memory = _Memory()
        self._audit: list[AuditEntry] = []

    def register_product(
        self, name: str, purpose: str, *, metadata: dict[str, Any] | None = None
    ) -> Product:
        """Register a product and return its stable public representation."""
        product = Product(name, purpose, metadata=metadata or {})
        self._products[product.id] = product
        self._record_audit("product.register", "success", target=product.name)
        return product

    def products(self) -> tuple[Product, ...]:
        """Return registered products."""
        return tuple(self._products.values())

    def add_knowledge(
        self,
        content: str,
        *,
        source: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeItem:
        """Add traceable knowledge without exposing the storage implementation."""
        if not content.strip():
            raise ValueError("knowledge content must not be empty")
        if not source.strip():
            raise ValueError("knowledge source must not be empty")
        item = KnowledgeItem(content, source, title, metadata=metadata or {})
        self._knowledge[item.id] = item
        self._record_audit("knowledge.add", "success", target=source)
        return item

    def search_knowledge(self, query: str, *, limit: int = 10) -> tuple[KnowledgeItem, ...]:
        """Search knowledge using a deterministic SDK-level contract."""
        if limit < 1:
            raise ValueError("limit must be positive")
        terms = tuple(part for part in query.casefold().split() if part)
        matches = [
            item
            for item in self._knowledge.values()
            if not terms
            or all(
                term in f"{item.title or ''} {item.content} {item.source}".casefold()
                for term in terms
            )
        ]
        return tuple(matches[:limit])

    def remember(self, value: str) -> None:
        """Store a short-lived SDK memory value."""
        if not value.strip():
            raise ValueError("memory value must not be empty")
        self._memory.items.append(value)

    def memories(self) -> tuple[str, ...]:
        """Return memory values in insertion order."""
        return tuple(self._memory.items)

    def create_task(self, objective: str, *, input: Any = None) -> Task:
        """Create a task without executing it."""
        if not objective.strip():
            raise ValueError("task objective must not be empty")
        task = Task(objective, input=input)
        self._tasks[task.id] = TaskResult(task.id, TaskStatus.QUEUED)
        self._record_audit("task.create", "success", task_id=str(task.id))
        return task

    def task_result(self, task_id: UUID) -> TaskResult | None:
        """Inspect the latest public result for a task."""
        return self._tasks.get(task_id)

    def register_agent(self, name: str, handler: AgentHandler) -> None:
        """Register an application-owned agent implementation."""
        if not name.strip():
            raise ValueError("agent name must not be empty")
        self._agents[name] = _RegisteredAgent(name, handler)

    async def run_agent(self, agent: str, task: Task) -> AgentResult:
        """Run a registered agent and normalize its result."""
        registered = self._agents.get(agent)
        if registered is None:
            raise KeyError(f"agent is not registered: {agent}")
        self._tasks[task.id] = TaskResult(task.id, TaskStatus.RUNNING)
        self._record_audit("agent.run", "started", task_id=str(task.id), agent=agent)
        try:
            output = registered.handler(task)
            if inspect.isawaitable(output):
                output = await output
            result = AgentResult(agent, task, output=output, completed=True)
            self._tasks[task.id] = TaskResult(task.id, TaskStatus.COMPLETED, output=output)
            self._record_audit("agent.run", "success", task_id=str(task.id), agent=agent)
            return result
        except Exception as exc:
            self._tasks[task.id] = TaskResult(task.id, TaskStatus.FAILED, error=str(exc))
            self._record_audit(
                "agent.run", "failed", task_id=str(task.id), agent=agent, failure=str(exc)
            )
            return AgentResult(agent, task, error=str(exc), completed=False)

    def register_tool(self, name: str, handler: ToolHandler) -> None:
        """Register an application-owned tool handler."""
        if not name.strip():
            raise ValueError("tool name must not be empty")
        self._tools[name] = handler

    async def execute(self, action: str, arguments: dict[str, Any]) -> ExecutionResult:
        """Execute a registered tool through the stable SDK boundary."""
        handler = self._tools.get(action)
        if handler is None:
            raise KeyError(f"tool is not registered: {action}")
        try:
            output = handler(arguments)
            if inspect.isawaitable(output):
                output = await output
            self._record_audit("tool.execute", "success", target=action)
            return ExecutionResult(action, True, output=output)
        except Exception as exc:
            self._record_audit("tool.execute", "failed", target=action, failure=str(exc))
            return ExecutionResult(action, False, error=str(exc))

    async def evaluate_idea(
        self, subject: str, evaluator: Evaluator | EvaluatorHandler
    ) -> EvaluationResult:
        """Evaluate an idea through an explicit application-owned evaluator."""
        if not subject.strip():
            raise ValueError("subject must not be empty")
        result = (
            evaluator.evaluate(subject) if hasattr(evaluator, "evaluate") else evaluator(subject)
        )
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, EvaluationResult):
            raise TypeError("evaluator must return EvaluationResult")
        self._record_audit("idea.evaluate", "success", target=subject)
        return result

    async def execute_engineering(
        self, task: Task, engineer: Engineer | EngineeringHandler
    ) -> EngineeringResult:
        """Execute an engineering task through an explicit engineering adapter."""
        self._record_audit("engineering.execute", "started", task_id=str(task.id))
        try:
            result = engineer.execute(task) if hasattr(engineer, "execute") else engineer(task)
            if inspect.isawaitable(result):
                result = await result
            status = str(getattr(result, "status", "completed"))
            summary = str(getattr(result, "summary", result))
            self._record_audit("engineering.execute", "success", task_id=str(task.id))
            return EngineeringResult(task, status, summary, raw=result)
        except Exception as exc:
            self._record_audit(
                "engineering.execute", "failed", task_id=str(task.id), failure=str(exc)
            )
            return EngineeringResult(task, "failed", str(exc), raw=None)

    async def orchestrate(
        self, workflow: str, task: Task, runner: Orchestrator | WorkflowHandler
    ) -> WorkflowResult:
        """Run an explicit workflow adapter without exposing orchestration internals."""
        if not workflow.strip():
            raise ValueError("workflow name must not be empty")
        try:
            output = runner.run(workflow, task) if hasattr(runner, "run") else runner(task)
            if inspect.isawaitable(output):
                output = await output
            self._record_audit("workflow.run", "success", task_id=str(task.id), target=workflow)
            return WorkflowResult(workflow, True, output=output)
        except Exception as exc:
            self._record_audit(
                "workflow.run", "failed", task_id=str(task.id), target=workflow, failure=str(exc)
            )
            return WorkflowResult(workflow, False, error=str(exc))

    def audit_history(self, *, limit: int | None = None) -> tuple[AuditEntry, ...]:
        """Return sanitized SDK audit history."""
        entries = tuple(self._audit)
        return entries if limit is None else entries[-limit:]

    def _record_audit(
        self,
        action: str,
        result: str,
        *,
        task_id: str | None = None,
        agent: str | None = None,
        target: str | None = None,
        failure: str | None = None,
    ) -> None:
        from datetime import UTC, datetime

        self._audit.append(
            AuditEntry(
                action,
                result,
                datetime.now(UTC).isoformat(),
                task_id,
                agent,
                target,
                failure,
            )
        )


__all__ = [
    "EIS",
    "Agent",
    "Engineer",
    "Evaluator",
    "Executor",
    "Orchestrator",
    "Tool",
]
