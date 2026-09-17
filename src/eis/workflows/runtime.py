"""End-to-end, resumable, governance-controlled engineering workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from eis.security.models import (
    ActionRequest,
    Approval,
    ApprovalRequest,
    ApprovalStatus,
    Principal,
    RiskLevel,
)
from eis.security.runtime import AuthorizationError, SecurityGateway
from eis.workflows.models import (
    WorkflowApproval,
    WorkflowEvent,
    WorkflowPhase,
    WorkflowReport,
    WorkflowRequest,
    WorkflowState,
    WorkflowStatus,
)
from eis.workflows.protocols import WorkflowOperations
from eis.workflows.store import WorkflowStore


class WorkflowEscalation(RuntimeError):
    """Raised internally when a workflow must stop for human intervention."""


@dataclass(slots=True)
class EngineeringWorkflow:
    """Drive the complete engineering lifecycle without bypassing security."""

    operations: WorkflowOperations
    security: SecurityGateway
    principal: Principal
    store: WorkflowStore
    approval_phases: frozenset[WorkflowPhase] = frozenset({WorkflowPhase.IMPLEMENT})
    _approval_cache: dict[str, Approval] = field(default_factory=dict)

    def start(self, request: WorkflowRequest) -> WorkflowState:
        state = WorkflowState(request=request, status=WorkflowStatus.PENDING)
        self.store.save(state)
        return state

    async def run(self, workflow_id: str) -> WorkflowReport:
        state = self.store.load(workflow_id)
        if state is None:
            raise KeyError(f"unknown workflow: {workflow_id}")
        if state.status in {
            WorkflowStatus.WAITING_APPROVAL,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.ESCALATED,
        }:
            return self._report(state)
        return await self._run(state)

    async def resume(self, workflow_id: str, approval: Approval | None = None) -> WorkflowReport:
        state = self.store.load(workflow_id)
        if state is None:
            raise KeyError(f"unknown workflow: {workflow_id}")
        if state.status is not WorkflowStatus.WAITING_APPROVAL:
            return self._report(state)
        if approval is None or approval.status is not ApprovalStatus.APPROVED:
            raise AuthorizationError("approved human decision required to resume workflow")
        if state.approval is None or approval.request_id != state.approval.approval_request_id:
            raise AuthorizationError("approval does not match workflow checkpoint")
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
                    detail=approval.reason or "human approval granted",
                    evidence=(f"approved-by:{approval.approver}",),
                ),
            ),
            approval=None,
            data=state.data,
            escalation_reason=None,
        )
        self.store.save(resumed)
        return await self._run(resumed)

    async def escalate(self, workflow_id: str, reason: str) -> WorkflowReport:
        state = self.store.load(workflow_id)
        if state is None:
            raise KeyError(f"unknown workflow: {workflow_id}")
        if not reason.strip():
            raise ValueError("escalation reason must not be empty")
        event = WorkflowEvent(
            phase=state.phase or WorkflowPhase.FINAL_REPORT,
            status="escalated",
            detail=reason,
            uncertainty=("human intervention required",),
        )
        updated = WorkflowState(
            request=state.request,
            status=WorkflowStatus.ESCALATED,
            phase_index=state.phase_index,
            events=(*state.events, event),
            approval=state.approval,
            data=state.data,
            escalation_reason=reason,
        )
        self.store.save(updated)
        return self._report(updated)

    async def _run(self, state: WorkflowState) -> WorkflowReport:
        current = WorkflowState(
            request=state.request,
            status=WorkflowStatus.RUNNING,
            phase_index=state.phase_index,
            events=state.events,
            approval=state.approval,
            data=state.data,
            escalation_reason=state.escalation_reason,
        )
        self.store.save(current)
        phases = tuple(WorkflowPhase)

        while current.phase_index < len(phases):
            phase = phases[current.phase_index]
            try:
                approval = await self._checkpoint(current, phase)
                if approval is None and phase in self.approval_phases:
                    waiting = self.store.load(str(current.request.id))
                    if waiting is None:
                        raise KeyError(f"workflow disappeared during approval checkpoint: {current.request.id}")
                    return self._report(waiting)
                event = await self._execute(current, phase, approval)
            except WorkflowEscalation as exc:
                return await self.escalate(str(current.request.id), str(exc))
            except Exception as exc:
                event = WorkflowEvent(
                    phase=phase,
                    status="failed",
                    detail=str(exc),
                    failures=(str(exc),),
                )
                failed = self._advance(current, event, WorkflowStatus.FAILED)
                self.store.save(failed)
                return self._report(failed)

            current = self._advance(current, event, WorkflowStatus.RUNNING)
            self.store.save(current)

        completed = WorkflowState(
            request=current.request,
            status=WorkflowStatus.COMPLETED,
            phase_index=current.phase_index,
            events=current.events,
            approval=None,
            data=current.data,
            escalation_reason=None,
        )
        self.store.save(completed)
        return self._report(completed)

    async def _checkpoint(self, state: WorkflowState, phase: WorkflowPhase) -> Approval | None:
        if phase not in self.approval_phases:
            return None
        cached = self._approval_cache.pop(str(state.request.id), None)
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
        approval = self.security.approval_gate.request(request)
        checkpoint = WorkflowApproval(
            phase=phase,
            resource=request.resource,
            reason=request.reason,
            approval_request_id=approval.request_id,
        )
        waiting = WorkflowState(
            request=state.request,
            status=WorkflowStatus.WAITING_APPROVAL,
            phase_index=state.phase_index,
            events=(
                *state.events,
                WorkflowEvent(
                    phase=WorkflowPhase.APPROVAL,
                    status="waiting",
                    detail=request.reason,
                    uncertainty=("execution has not been authorized",),
                ),
            ),
            approval=checkpoint,
            data=state.data,
            escalation_reason=None,
        )
        self.store.save(waiting)
        return None

    async def _execute(
        self, state: WorkflowState, phase: WorkflowPhase, approval: Approval | None
    ) -> WorkflowEvent:
        is_write = phase in {WorkflowPhase.IMPLEMENT, WorkflowPhase.CORRECT}
        action = ActionRequest(
            actor=self.principal,
            action="write" if is_write else "read",
            resource=state.request.repository,
            risk_level=RiskLevel.HIGH if phase in self.approval_phases else RiskLevel.LOW,
            tool=f"workflow.{phase.value}",
            target=state.request.repository,
            task_id=state.request.id,
        )
        self.security.prepare(action, approval=approval)
        try:
            event = await self.operations.execute(phase, state)
        except Exception as exc:
            self.security.complete(action, result="failure", failure=str(exc))
            raise
        self.security.complete(action)
        return event

    @staticmethod
    def _advance(
        state: WorkflowState, event: WorkflowEvent, status: WorkflowStatus
    ) -> WorkflowState:
        return WorkflowState(
            request=state.request,
            status=status,
            phase_index=state.phase_index + 1,
            events=(*state.events, event),
            approval=None,
            data=state.data,
            escalation_reason=None,
        )

    @staticmethod
    def _report(state: WorkflowState) -> WorkflowReport:
        events = state.events
        completed = tuple(event.detail for event in events if event.status == "completed" and event.detail)
        evidence = tuple(item for event in events for item in event.evidence)
        tests = tuple(event.detail for event in events if event.phase is WorkflowPhase.TEST and event.detail)
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
