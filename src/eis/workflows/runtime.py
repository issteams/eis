from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from eis.security.models import (
    ActionRequest,
    Approval,
    ApprovalRequest,
    ApprovalStatus,
    Principal,
    RiskLevel,
)
from eis.security.runtime import SecurityGateway

from .models import (
    WorkflowEvent,
    WorkflowPhase,
    WorkflowReport,
    WorkflowRequest,
    WorkflowState,
    WorkflowStatus,
)
from .protocols import WorkflowOperations, WorkflowStore


@dataclass(slots=True)
class EngineeringWorkflow:
    operations: WorkflowOperations
    security: SecurityGateway
    principal: Principal
    store: WorkflowStore
    approval_phases: frozenset[WorkflowPhase] = frozenset({WorkflowPhase.IMPLEMENT})

    def __post_init__(self) -> None:
        self._approval_cache: dict[str, Approval] = {}

    async def start(self, request: WorkflowRequest) -> WorkflowReport:
        state = WorkflowState(
            request=request,
            status=WorkflowStatus.PENDING,
            phase_index=0,
            events=(),
            approval=None,
            data={},
            escalation_reason=None,
        )
        await self.store.save(state)
        return await self.run(request.id)

    async def run(self, workflow_id: str) -> WorkflowReport:
        state = await self.store.load(workflow_id)
        if state is None:
            raise KeyError(f"workflow {workflow_id!r} not found")
        if state.status in {
            WorkflowStatus.WAITING_APPROVAL,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.ESCALATED,
        }:
            return self._report(state)
        return await self._run(state)

    async def resume(
        self, workflow_id: str, approval: Approval | None = None
    ) -> WorkflowReport:
        state = await self.store.load(workflow_id)
        if state is None:
            raise KeyError(f"workflow {workflow_id!r} not found")
        if state.status is not WorkflowStatus.WAITING_APPROVAL:
            return self._report(state)
        if approval is None or approval.status is not ApprovalStatus.APPROVED:
            raise PermissionError("approved workflow checkpoint is required")
        if state.approval is None or approval.request_id != state.approval.approval_request_id:
            raise PermissionError("approval does not match workflow checkpoint")
        self._approval_cache[workflow_id] = approval
        resumed = WorkflowState(
            request=state.request,
            status=WorkflowStatus.RUNNING,
            phase_index=state.phase_index,
            events=(
                *state.events,
                WorkflowEvent(
                    phase=WorkflowPhase.APPROVAL,
                    status="completed",
                    detail=approval.reason,
                    evidence=(),
                    failures=(),
                    corrections=(),
                    risks=(),
                    uncertainty=(),
                ),
            ),
            approval=state.approval,
            data=state.data,
            escalation_reason=None,
        )
        await self.store.save(resumed)
        return await self._run(resumed)

    async def escalate(self, workflow_id: str, reason: str) -> WorkflowReport:
        state = await self.store.load(workflow_id)
        if state is None:
            raise KeyError(f"workflow {workflow_id!r} not found")
        escalated = WorkflowState(
            request=state.request,
            status=WorkflowStatus.ESCALATED,
            phase_index=state.phase_index,
            events=(
                *state.events,
                WorkflowEvent(
                    phase=WorkflowPhase.ESCALATE,
                    status="escalated",
                    detail=reason,
                    evidence=(),
                    failures=(),
                    corrections=(),
                    risks=(reason,),
                    uncertainty=(),
                ),
            ),
            approval=state.approval,
            data=state.data,
            escalation_reason=reason,
        )
        await self.store.save(escalated)
        return self._report(escalated)

    async def _run(self, state: WorkflowState) -> WorkflowReport:
        current = WorkflowState(
            request=state.request,
            status=WorkflowStatus.RUNNING,
            phase_index=state.phase_index,
            events=state.events,
            approval=state.approval,
            data=state.data,
            escalation_reason=None,
        )
        await self.store.save(current)
        phases = tuple(WorkflowPhase)
        while current.phase_index < len(phases):
            phase = phases[current.phase_index]
            approval = await self._checkpoint(current, phase)
            if approval is None and phase in self.approval_phases:
                waiting = await self.store.load(current.request.id)
                if waiting is None:
                    raise RuntimeError("workflow checkpoint was not persisted")
                return self._report(waiting)
            try:
                event = await self._execute(current, phase, approval)
            except Exception as exc:
                failed = WorkflowState(
                    request=current.request,
                    status=WorkflowStatus.FAILED,
                    phase_index=current.phase_index,
                    events=(
                        *current.events,
                        WorkflowEvent(
                            phase=phase,
                            status="failed",
                            detail=str(exc),
                            evidence=(),
                            failures=(str(exc),),
                            corrections=(),
                            risks=(),
                            uncertainty=(),
                        ),
                    ),
                    approval=current.approval,
                    data=current.data,
                    escalation_reason=None,
                )
                await self.store.save(failed)
                return self._report(failed)
            current = self._advance(current, event)
            await self.store.save(current)
        completed = WorkflowState(
            request=current.request,
            status=WorkflowStatus.COMPLETED,
            phase_index=current.phase_index,
            events=current.events,
            approval=None,
            data=current.data,
            escalation_reason=None,
        )
        await self.store.save(completed)
        return self._report(completed)

    async def _checkpoint(
        self, state: WorkflowState, phase: WorkflowPhase
    ) -> Approval | None:
        if phase not in self.approval_phases:
            return None
        cached = self._approval_cache.pop(state.request.id, None)
        if cached is not None:
            return cached
        request = ApprovalRequest(
            action=f"workflow.{phase.value}",
            resource=state.request.repository,
            actor=self.principal.id,
            reason=f"Human approval required before {phase.value}",
            risk_level=RiskLevel.HIGH,
            task_id=state.request.id,
        )
        approval_request = await self.security.approval_gate.request(request)
        checkpoint = WorkflowState(
            request=state.request,
            status=WorkflowStatus.WAITING_APPROVAL,
            phase_index=state.phase_index,
            events=(
                *state.events,
                WorkflowEvent(
                    phase=WorkflowPhase.APPROVAL,
                    status="waiting",
                    detail=request.reason,
                    evidence=(),
                    failures=(),
                    corrections=(),
                    risks=(),
                    uncertainty=(),
                ),
            ),
            approval=state.approval.__class__(
                phase=phase,
                resource=state.request.repository,
                reason=request.reason,
                approval_request_id=approval_request.id,
            )
            if state.approval is not None
            else __import__("eis.workflows.models", fromlist=["WorkflowApproval"]).WorkflowApproval(
                phase=phase,
                resource=state.request.repository,
                reason=request.reason,
                approval_request_id=approval_request.id,
            ),
            data=state.data,
            escalation_reason=None,
        )
        await self.store.save(checkpoint)
        return None

    async def _execute(
        self, state: WorkflowState, phase: WorkflowPhase, approval: Approval | None
    ) -> WorkflowEvent:
        action = ActionRequest(
            actor=self.principal.id,
            action=f"workflow.{phase.value}",
            resource=state.request.repository,
            risk=RiskLevel.HIGH if phase is WorkflowPhase.IMPLEMENT else RiskLevel.MEDIUM,
            target=state.request.id,
        )
        authorization = await self.security.prepare(action, approval=approval)
        result = await self.operations.execute(phase, state)
        await self.security.complete(authorization, success=True)
        return result

    @staticmethod
    def _advance(state: WorkflowState, event: WorkflowEvent) -> WorkflowState:
        return WorkflowState(
            request=state.request,
            status=WorkflowStatus.RUNNING,
            phase_index=state.phase_index + 1,
            events=(*state.events, event),
            approval=None,
            data=state.data,
            escalation_reason=None,
        )

    @staticmethod
    def _report(state: WorkflowState) -> WorkflowReport:
        events = state.events
        completed = tuple(
            event.detail for event in events if event.status == "completed" and event.detail
        )
        evidence = tuple(item for event in events for item in event.evidence)
        tests = tuple(
            event.detail
            for event in events
            if event.phase is WorkflowPhase.TEST and event.detail
        )
        failures = tuple(item for event in events for item in event.failures)
        corrections = tuple(item for event in events for item in event.corrections)
        risks = tuple(item for event in events for item in event.risks)
        uncertainty = tuple(item for event in events for item in event.uncertainty)
        decisions = tuple(
            event.detail
            for event in events
            if event.phase is WorkflowPhase.APPROVAL and event.status == "completed"
        )
        return WorkflowReport(
            request=state.request,
            status=state.status,
            events=events,
            completed_work=completed,
            evidence=evidence,
            tests=tests,
            failures=failures,
            corrections=corrections,
            remaining_risks=risks,
            remaining_uncertainty=uncertainty,
            human_decisions=decisions,
            escalation_reason=state.escalation_reason,
        )
