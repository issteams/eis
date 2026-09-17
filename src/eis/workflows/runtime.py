"""Runtime for governed, resumable engineering workflows."""

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
from eis.security.runtime import SecurityGateway

from .models import (
    WorkflowApproval,
    WorkflowEvent,
    WorkflowPhase,
    WorkflowReport,
    WorkflowRequest,
    WorkflowState,
    WorkflowStatus,
)
from .protocols import WorkflowOperations
from .store import WorkflowStore


class WorkflowEscalation(RuntimeError):
    """Raised when a workflow must stop and require human intervention."""


@dataclass(slots=True)
class EngineeringWorkflow:
    """Execute the engineering lifecycle with persistence and governance gates."""

    operations: WorkflowOperations
    security: SecurityGateway
    principal: Principal
    store: WorkflowStore
    approval_phases: frozenset[WorkflowPhase] = frozenset({WorkflowPhase.IMPLEMENT})
    _approval_cache: dict[str, Approval] = field(default_factory=dict, init=False, repr=False)

    def start(self, request: WorkflowRequest) -> WorkflowState:
        """Create and persist a new workflow without executing it."""
        state = WorkflowState(request=request)
        self.store.save(state)
        return state

    async def run(self, workflow_id: str) -> WorkflowReport:
        """Run or resume a persisted workflow until a terminal/checkpoint state."""
        state = self.store.load(workflow_id)
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

    async def resume(self, workflow_id: str, approval: Approval | None = None) -> WorkflowReport:
        """Resume a waiting workflow only with its matching approved checkpoint."""
        state = self.store.load(workflow_id)
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
                    detail=approval.reason or "workflow implementation approved",
                ),
            ),
            approval=state.approval,
            data=state.data,
        )
        self.store.save(resumed)
        return await self._run(resumed)

    async def escalate(self, workflow_id: str, reason: str) -> WorkflowReport:
        """Persist a workflow escalation and stop autonomous execution."""
        state = self.store.load(workflow_id)
        if state is None:
            raise KeyError(f"workflow {workflow_id!r} not found")
        escalated = WorkflowState(
            request=state.request,
            status=WorkflowStatus.ESCALATED,
            phase_index=state.phase_index,
            events=(
                *state.events,
                WorkflowEvent(
                    phase=WorkflowPhase.APPROVAL,
                    status="escalated",
                    detail=reason,
                    risks=(reason,),
                    uncertainty=("human intervention required",),
                ),
            ),
            approval=state.approval,
            data=state.data,
            escalation_reason=reason,
        )
        self.store.save(escalated)
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
        self.store.save(current)
        phases = tuple(WorkflowPhase)
        while current.phase_index < len(phases):
            phase = phases[current.phase_index]
            approval = self._checkpoint(current, phase)
            if approval is None and phase in self.approval_phases:
                waiting = self.store.load(str(current.request.id))
                if waiting is None:
                    raise RuntimeError("workflow checkpoint was not persisted")
                return self._report(waiting)
            try:
                event = await self._execute(current, phase, approval)
            except WorkflowEscalation:
                raise
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
                            failures=(str(exc),),
                        ),
                    ),
                    approval=current.approval,
                    data=current.data,
                )
                self.store.save(failed)
                return self._report(failed)
            current = self._advance(current, event)
            self.store.save(current)
        completed = WorkflowState(
            request=current.request,
            status=WorkflowStatus.COMPLETED,
            phase_index=current.phase_index,
            events=current.events,
            data=current.data,
        )
        self.store.save(completed)
        return self._report(completed)

    def _checkpoint(self, state: WorkflowState, phase: WorkflowPhase) -> Approval | None:
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
        approval_request = self.security.approval_gate.request(request)
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
                ),
            ),
            approval=WorkflowApproval(
                phase=phase,
                resource=state.request.repository,
                reason=request.reason,
                approval_request_id=approval_request.request_id,
            ),
            data=state.data,
        )
        self.store.save(checkpoint)
        return None

    async def _execute(
        self, state: WorkflowState, phase: WorkflowPhase, approval: Approval | None
    ) -> WorkflowEvent:
        action = ActionRequest(
            actor=self.principal,
            action="write" if phase is WorkflowPhase.IMPLEMENT else "read",
            resource=state.request.repository,
            risk_level=RiskLevel.HIGH if phase is WorkflowPhase.IMPLEMENT else RiskLevel.MEDIUM,
            target=str(state.request.id),
            task_id=state.request.id,
        )
        self.security.prepare(action, approval=approval)
        try:
            result = await self.operations.execute(phase, state)
        except Exception as exc:
            self.security.complete(action, result="failure", failure=str(exc))
            raise
        self.security.complete(action)
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
            event.detail for event in events if event.phase is WorkflowPhase.TEST and event.detail
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