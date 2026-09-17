from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from eis.sdk.models import (
    AgentResult,
    AuditEntry,
    EngineeringResult,
    EvaluationResult,
    ExecutionResult,
    KnowledgeItem,
    MemoryItem,
    Product,
    Task,
    TaskResult,
    TaskStatus,
    WorkflowResult,
)


class Agent(Protocol):
    name: str

    async def run(self, task: Task) -> AgentResult: ...


class Evaluator(Protocol):
    def evaluate(self, subject: str) -> EvaluationResult | Awaitable[EvaluationResult]: ...


class Engineer(Protocol):
    def execute(self, task: Task) -> Any: ...


class Executor(Protocol):
    def execute(self, action: str, **kwargs: Any) -> ExecutionResult | Awaitable[ExecutionResult]: ...


class Orchestrator(Protocol):
    def run(self, workflow: str, task: Task) -> Any: ...


class Tool(Protocol):
    name: str

    def execute(self, **kwargs: Any) -> Any: ...


AgentHandler = Callable[[Task], AgentResult | Awaitable[AgentResult]]
EvaluatorHandler = Callable[[str], EvaluationResult | Awaitable[EvaluationResult]]
EngineeringHandler = Callable[[Task], Any]
WorkflowHandler = Callable[[Task], Any]
ToolHandler = Callable[..., Any]


@dataclass(slots=True)
class _RegisteredAgent:
    name: str
    handler: AgentHandler


@dataclass(slots=True)
class _Memory:
    content: str
    metadata: dict[str, Any]


class EIS:
    """Stable public facade for the Echowavs Intelligent System SDK."""

    def __init__(self) -> None:
        self._products: dict[str, Product] = {}
        self._knowledge: list[KnowledgeItem] = []
        self._memories: list[_Memory] = []
        self._tasks: dict[UUID, Task] = {}
        self._results: dict[UUID, TaskResult] = {}
        self._agents: dict[str, _RegisteredAgent] = {}
        self._tools: dict[str, ToolHandler] = {}
        self._audit: list[AuditEntry] = []

    def register_product(self, product: Product) -> Product:
        """Register an Echowavs product with EIS."""
        self._products[product.name] = product
        self._record_audit("product.register", "success", target=product.name)
        return product

    def products(self) -> tuple[Product, ...]:
        """Return registered products."""
        return tuple(self._products.values())

    def add_knowledge(self, item: KnowledgeItem) -> KnowledgeItem:
        """Add a knowledge item to the SDK knowledge collection."""
        self._knowledge.append(item)
        self._record_audit("knowledge.add", "success", target=item.title)
        return item

    def search_knowledge(self, query: str) -> tuple[KnowledgeItem, ...]:
        """Perform simple case-insensitive knowledge lookup."""
        normalized = query.strip().lower()
        if not normalized:
            return tuple(self._knowledge)
        return tuple(
            item
            for item in self._knowledge
            if normalized in f"{item.title} {item.content}".lower()
        )

    def remember(self, content: str, *, metadata: dict[str, Any] | None = None) -> MemoryItem:
        """Store a memory through the stable SDK API."""
        if not content.strip():
            raise ValueError("content must not be empty")
        item = MemoryItem(content=content, metadata=metadata or {})
        self._memories.append(_Memory(item.content, item.metadata))
        self._record_audit("memory.add", "success")
        return item

    def memories(self) -> tuple[MemoryItem, ...]:
        """Return stored memories."""
        return tuple(MemoryItem(content=m.content, metadata=m.metadata) for m in self._memories)

    def create_task(self, objective: str, *, input: dict[str, Any] | None = None) -> Task:
        """Create and retain a task."""
        task = Task(objective=objective, input=input or {})
        self._tasks[task.id] = task
        self._record_audit("task.create", "success", task_id=str(task.id))
        return task

    def task_result(self, task_id: UUID) -> TaskResult | None:
        """Return a stored task result, if available."""
        return self._results.get(task_id)

    def register_agent(self, name: str, handler: AgentHandler) -> None:
        """Register an application-owned agent adapter."""
        if not name.strip():
            raise ValueError("agent name must not be empty")
        self._agents[name] = _RegisteredAgent(name, handler)
        self._record_audit("agent.register", "success", agent=name)

    async def run_agent(self, name: str, task: Task) -> AgentResult:
        """Run a registered agent and return its typed result."""
        try:
            result = self._agents[name].handler(task)
        except KeyError as exc:
            raise KeyError(f"unknown agent: {name}") from exc
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, AgentResult):
            raise TypeError("agent handler must return AgentResult")
        self._record_audit("agent.run", "success", task_id=str(task.id), agent=name)
        return result

    def register_tool(self, name: str, handler: ToolHandler) -> None:
        """Register an application-owned tool adapter."""
        if not name.strip():
            raise ValueError("tool name must not be empty")
        self._tools[name] = handler
        self._record_audit("tool.register", "success", target=name)

    async def execute(self, name: str, **kwargs: Any) -> ExecutionResult:
        """Execute a registered tool through the public SDK boundary."""
        try:
            handler = self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc
        result = handler(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, ExecutionResult):
            raise TypeError("tool handler must return ExecutionResult")
        self._record_audit("tool.execute", "success", target=name)
        return result

    async def evaluate_idea(
        self,
        subject: str,
        evaluator: Evaluator | EvaluatorHandler,
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
        self,
        task: Task,
        engineer: Engineer | EngineeringHandler,
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
        self,
        workflow: str,
        task: Task,
        runner: Orchestrator | WorkflowHandler,
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
