"""Protocols used by the autonomous engineering workflow."""

from __future__ import annotations

from typing import Protocol

from eis.context.models import ContextRequest, ContextResult
from eis.engineering.models import (
    EngineeringPlan,
    EngineeringTask,
    FileChange,
    RepositorySnapshot,
)
from eis.tools.models import ToolRequest, ToolResult


class KnowledgeRetriever(Protocol):
    async def retrieve(self, request: ContextRequest) -> ContextResult: ...


class RepositoryInspector(Protocol):
    async def inspect(self, repository: str) -> RepositorySnapshot: ...


class EngineeringPlanner(Protocol):
    async def plan(
        self, task: EngineeringTask, snapshot: RepositorySnapshot, context: ContextResult
    ) -> EngineeringPlan: ...


class PlanValidator(Protocol):
    async def validate(
        self, task: EngineeringTask, snapshot: RepositorySnapshot, plan: EngineeringPlan
    ) -> tuple[bool, str]: ...


class EngineeringToolRunner(Protocol):
    async def execute(self, request: ToolRequest) -> ToolResult: ...


class ChangeTracker(Protocol):
    def record(self, change: FileChange) -> None: ...
    def changes(self) -> tuple[FileChange, ...]: ...


class FailureAnalyzer(Protocol):
    async def analyze(self, result: ToolResult) -> str: ...
