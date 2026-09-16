"""Controlled autonomous engineering orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from eis.context.models import ContextRequest, ContextResult
from eis.engineering.models import (
    ChangeRecord,
    EngineeringLimits,
    EngineeringPhase,
    EngineeringPlan,
    EngineeringReport,
    EngineeringTask,
    FileChange,
    RepositorySnapshot,
)
from eis.engineering.protocols import (
    ChangeTracker,
    EngineeringPlanner,
    EngineeringToolRunner,
    FailureAnalyzer,
    KnowledgeRetriever,
    PlanValidator,
    RepositoryInspector,
)
from eis.tools.models import ExecutionStatus, ToolRequest, ToolResult


class EngineeringEscalation(RuntimeError):
    """Raised when autonomous engineering cannot safely continue."""


@dataclass(slots=True)
class InMemoryChangeTracker:
    _items: list[FileChange] = field(default_factory=list)

    def record(self, change: FileChange) -> None:
        if change.path not in {item.path for item in self._items}:
            self._items.append(change)

    def changes(self) -> tuple[FileChange, ...]:
        return tuple(self._items)


class EngineeringAgent:
    """Run a bounded repository-aware implementation workflow."""

    def __init__(
        self,
        retriever: KnowledgeRetriever,
        inspector: RepositoryInspector,
        planner: EngineeringPlanner,
        validator: PlanValidator,
        tools: EngineeringToolRunner,
        *,
        failure_analyzer: FailureAnalyzer | None = None,
        change_tracker: ChangeTracker | None = None,
        limits: EngineeringLimits | None = None,
    ) -> None:
        self._retriever = retriever
        self._inspector = inspector
        self._planner = planner
        self._validator = validator
        self._tools = tools
        self._failure_analyzer = failure_analyzer
        self._tracker = change_tracker or InMemoryChangeTracker()
        self._limits = limits or EngineeringLimits()
        self._calls = 0
        self._started = 0.0

    async def run(self, task: EngineeringTask) -> EngineeringReport:
        self._calls = 0
        self._started = time.monotonic()
        records: list[ChangeRecord] = []
        tests: list[str] = []
        failures: list[str] = []
        plan: EngineeringPlan | None = None
        iterations = 0

        try:
            self._guard()
            records.append(ChangeRecord(EngineeringPhase.UNDERSTAND, detail=task.objective))
            context = await self._retrieve(task)
            records.append(
                ChangeRecord(
                    EngineeringPhase.RETRIEVE,
                    detail="project knowledge retrieved",
                )
            )
            snapshot = await self._inspect(task)
            records.append(
                ChangeRecord(
                    EngineeringPhase.INSPECT,
                    detail=f"inspected {len(snapshot.files)} repository files",
                )
            )
            records.append(
                ChangeRecord(
                    EngineeringPhase.ARCHITECTURE,
                    detail="architecture inspection complete",
                )
            )
            records.append(
                ChangeRecord(
                    EngineeringPhase.AFFECTED_COMPONENTS,
                    detail="affected components identified by planner input",
                )
            )
            records.append(
                ChangeRecord(
                    EngineeringPhase.EXISTING_FUNCTIONALITY,
                    detail="existing functionality supplied to planner",
                )
            )
            records.append(
                ChangeRecord(
                    EngineeringPhase.DUPLICATION,
                    detail="duplication candidates supplied to planner",
                )
            )

            self._guard()
            plan = await self._planner.plan(task, snapshot, context)
            records.append(ChangeRecord(EngineeringPhase.PLAN, detail=plan.rationale))
            self._guard()
            valid, reason = await self._validator.validate(task, snapshot, plan)
            records.append(ChangeRecord(EngineeringPhase.VALIDATE_PLAN, detail=reason))
            if not valid:
                raise EngineeringEscalation(
                    f"implementation plan rejected: {reason}"
                )

            while iterations < self._limits.max_iterations:
                iterations += 1
                self._guard()
                implementation = await self._call_tool(
                    "engineering.implement",
                    {
                        "task": task.objective,
                        "repository": task.repository,
                        "plan": plan,
                    },
                )
                changes = self._record_changes(implementation)
                records.append(
                    ChangeRecord(EngineeringPhase.IMPLEMENT, changes=changes)
                )
                self._enforce_file_limit()

                targeted = await self._call_tool(
                    "engineering.test.targeted",
                    {"repository": task.repository, "plan": plan},
                )
                tests.append("targeted tests")
                if targeted.status is not ExecutionStatus.SUCCESS:
                    failure = await self._failure(targeted)
                    failures.append(failure)
                    records.append(
                        ChangeRecord(
                            EngineeringPhase.ANALYZE_FAILURES,
                            detail=failure,
                        )
                    )
                    if iterations >= self._limits.max_iterations:
                        raise EngineeringEscalation(
                            "maximum engineering iterations reached"
                        )
                    await self._call_tool(
                        "engineering.correct",
                        {
                            "repository": task.repository,
                            "failure": failure,
                            "plan": plan,
                        },
                    )
                    records.append(
                        ChangeRecord(
                            EngineeringPhase.CORRECT,
                            detail=failure,
                        )
                    )
                    continue

                records.append(
                    ChangeRecord(EngineeringPhase.TARGETED_TESTS, detail="passed")
                )
                broader = await self._call_tool(
                    "engineering.test.broader",
                    {"repository": task.repository, "plan": plan},
                )
                tests.append("broader tests")
                if broader.status is not ExecutionStatus.SUCCESS:
                    failure = await self._failure(broader)
                    failures.append(failure)
                    records.append(
                        ChangeRecord(
                            EngineeringPhase.ANALYZE_FAILURES,
                            detail=failure,
                        )
                    )
                    if iterations >= self._limits.max_iterations:
                        raise EngineeringEscalation(
                            "maximum engineering iterations reached"
                        )
                    await self._call_tool(
                        "engineering.correct",
                        {
                            "repository": task.repository,
                            "failure": failure,
                            "plan": plan,
                        },
                    )
                    records.append(
                        ChangeRecord(
                            EngineeringPhase.CORRECT,
                            detail=failure,
                        )
                    )
                    continue

                records.append(
                    ChangeRecord(EngineeringPhase.BROADER_TESTS, detail="passed")
                )
                records.append(
                    ChangeRecord(
                        EngineeringPhase.REPORT,
                        detail="implementation verified",
                    )
                )
                return EngineeringReport(
                    task,
                    "completed",
                    plan,
                    tuple(records),
                    tuple(tests),
                    tuple(failures),
                    iterations,
                    self._calls,
                    summary=self._summary(plan, tests, changes),
                )

            raise EngineeringEscalation("maximum engineering iterations reached")
        except EngineeringEscalation as exc:
            records.append(ChangeRecord(EngineeringPhase.ESCALATE, detail=str(exc)))
            return EngineeringReport(
                task,
                "escalated",
                plan,
                tuple(records),
                tuple(tests),
                tuple(failures),
                iterations,
                self._calls,
                escalated=True,
                escalation_reason=str(exc),
                summary="Engineering stopped before safe completion.",
            )

    async def _retrieve(self, task: EngineeringTask) -> ContextResult:
        self._guard()
        return await self._retriever.retrieve(ContextRequest(task.objective))

    async def _inspect(self, task: EngineeringTask) -> RepositorySnapshot:
        self._guard()
        return await self._inspector.inspect(task.repository)

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        self._guard()
        self._calls += 1
        return await self._tools.execute(ToolRequest(name, arguments))

    async def _failure(self, result: ToolResult) -> str:
        if self._failure_analyzer is not None:
            self._guard()
            self._calls += 1
            return await self._failure_analyzer.analyze(result)
        return result.error or result.stderr or "engineering tool failed"

    def _record_changes(self, result: ToolResult) -> tuple[FileChange, ...]:
        output = result.output
        raw_changes = output.get("changes", ()) if isinstance(output, dict) else ()
        changes: list[FileChange] = []
        for item in raw_changes:
            if isinstance(item, FileChange):
                change = item
            elif isinstance(item, dict) and isinstance(item.get("path"), str):
                change = FileChange(
                    item["path"],
                    str(item.get("operation", "modify")),
                    str(item.get("summary", "")),
                )
            else:
                continue
            self._tracker.record(change)
            changes.append(change)
        return tuple(changes)

    def _enforce_file_limit(self) -> None:
        if len(self._tracker.changes()) > self._limits.max_files_changed:
            raise EngineeringEscalation("maximum changed-file limit reached")

    def _guard(self) -> None:
        if self._calls >= self._limits.max_tool_calls:
            raise EngineeringEscalation("maximum tool-call limit reached")
        if time.monotonic() - self._started >= self._limits.max_execution_seconds:
            raise EngineeringEscalation("maximum execution time reached")

    @staticmethod
    def _summary(
        plan: EngineeringPlan, tests: list[str], changes: tuple[FileChange, ...]
    ) -> str:
        return (
            f"Implemented {plan.objective!r} using {len(changes)} changed file(s); "
            f"verification completed with {len(tests)} test stages."
        )
