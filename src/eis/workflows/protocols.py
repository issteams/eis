"""Protocols separating workflow orchestration from engineering capabilities."""

from __future__ import annotations

from typing import Protocol

from eis.workflows.models import WorkflowEvent, WorkflowPhase, WorkflowState


class WorkflowOperations(Protocol):
    async def execute(self, phase: WorkflowPhase, state: WorkflowState) -> WorkflowEvent: ...


class WorkflowEscalator(Protocol):
    async def escalate(self, state: WorkflowState, reason: str) -> WorkflowEvent: ...
