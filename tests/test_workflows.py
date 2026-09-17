from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from eis.security.models import Permission, Principal, Role
from eis.security.runtime import InMemoryAuditSink, RoleAuthorizer, SecurityGateway
from eis.workflows import (
    EngineeringWorkflow,
    WorkflowEvent,
    WorkflowPhase,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStore,
)


class Operations:
    def __init__(self) -> None:
        self.phases: list[WorkflowPhase] = []

    async def execute(self, phase: WorkflowPhase, state: Any) -> WorkflowEvent:
        self.phases.append(phase)
        if phase is WorkflowPhase.TEST:
            return WorkflowEvent(
                phase=phase,
                status="completed",
                detail="pytest passed",
                evidence=("test-run:success",),
            )
        if phase is WorkflowPhase.SECURITY_REVIEW:
            return WorkflowEvent(
                phase=phase,
                status="completed",
                detail="security review completed",
                risks=("external deployment remains human-controlled",),
            )
        if phase is WorkflowPhase.FINAL_REPORT:
            return WorkflowEvent(
                phase=phase,
                status="completed",
                detail="final report prepared",
            )
        return WorkflowEvent(
            phase=phase,
            status="completed",
            detail=f"completed {phase.value}",
        )


@pytest.fixture
def workflow_factory(tmp_path: Path) -> tuple[EngineeringWorkflow, Operations, SecurityGateway]:
    principal = Principal("workflow", roles=frozenset({"engineer"}))
    role = Role(
        "engineer",
        frozenset({Permission("read", "*"), Permission("write", "*")}),
    )
    security = SecurityGateway(
        RoleAuthorizer(
            roles={"engineer": role},
            principals={principal.id: principal},
        ),
        InMemoryAuditSink(),
    )
    operations = Operations()
    workflow = EngineeringWorkflow(
        operations,
        security,
        principal,
        WorkflowStore(tmp_path / "workflows.sqlite3"),
    )
    return workflow, operations, security


@pytest.mark.anyio
async def test_workflow_stops_at_human_approval_and_resumes(
    workflow_factory: tuple[EngineeringWorkflow, Operations, SecurityGateway],
) -> None:
    workflow, operations, security = workflow_factory
    request = WorkflowRequest("Add feature X to product Y", "product-y")
    state = workflow.start(request)

    waiting = await workflow.run(str(state.request.id))

    assert waiting.status is WorkflowStatus.WAITING_APPROVAL
    checkpoint = workflow.store.load(request.id)
    assert checkpoint is not None
    assert checkpoint.approval is not None
    assert WorkflowPhase.IMPLEMENT not in operations.phases

    pending = security.approval_gate.approvals[str(checkpoint.approval.approval_request_id)]
    approved = security.approval_gate.resolve(
        pending,
        approver="human",
        approved=True,
        reason="implementation approved",
    )
    completed = await workflow.resume(str(request.id), approved)

    assert completed.status is WorkflowStatus.COMPLETED
    assert operations.phases[-1] is WorkflowPhase.FINAL_REPORT
    assert "pytest passed" in completed.tests
    assert "test-run:success" in completed.evidence
    assert completed.remaining_risks
    assert "implementation approved" in completed.human_decisions


@pytest.mark.anyio
async def test_workflow_rejects_missing_or_mismatched_approval(
    workflow_factory: tuple[EngineeringWorkflow, Operations, SecurityGateway],
) -> None:
    workflow, _, security = workflow_factory
    request = WorkflowRequest("Implement change", "repo")
    workflow.start(request)
    waiting = await workflow.run(str(request.id))
    checkpoint = workflow.store.load(request.id)
    assert waiting.status is WorkflowStatus.WAITING_APPROVAL
    assert checkpoint is not None and checkpoint.approval is not None

    with pytest.raises(PermissionError):
        await workflow.resume(str(request.id))

    pending = security.approval_gate.approvals[str(checkpoint.approval.approval_request_id)]
    rejected = security.approval_gate.resolve(
        pending,
        approver="human",
        approved=False,
        reason="not ready",
    )
    with pytest.raises(PermissionError):
        await workflow.resume(str(request.id), rejected)


@pytest.mark.anyio
async def test_workflow_persists_interrupted_state(
    workflow_factory: tuple[EngineeringWorkflow, Operations, SecurityGateway],
) -> None:
    workflow, _, _ = workflow_factory
    request = WorkflowRequest("Inspect architecture", "repo")
    workflow.start(request)
    await workflow.run(str(request.id))

    restored = workflow.store.load(request.id)
    assert restored is not None
    assert restored.status is WorkflowStatus.WAITING_APPROVAL
    assert restored.phase is WorkflowPhase.IMPLEMENT


@pytest.mark.anyio
async def test_workflow_escalation_is_persisted(
    workflow_factory: tuple[EngineeringWorkflow, Operations, SecurityGateway],
) -> None:
    workflow, _, _ = workflow_factory
    request = WorkflowRequest("Change production infrastructure", "repo")
    workflow.start(request)

    report = await workflow.escalate(
        str(request.id),
        "production scope requires human decision",
    )

    assert report.status is WorkflowStatus.ESCALATED
    assert report.escalation_reason == "production scope requires human decision"
    assert report.remaining_uncertainty == ("human intervention required",)


@pytest.mark.anyio
async def test_completed_workflow_is_idempotent_after_completion(
    workflow_factory: tuple[EngineeringWorkflow, Operations, SecurityGateway],
) -> None:
    workflow, operations, security = workflow_factory
    request = WorkflowRequest("Add safe feature", "repo")
    workflow.start(request)
    waiting = await workflow.run(str(request.id))
    checkpoint = workflow.store.load(request.id)
    assert waiting.status is WorkflowStatus.WAITING_APPROVAL
    assert checkpoint is not None and checkpoint.approval is not None
    pending = security.approval_gate.approvals[str(checkpoint.approval.approval_request_id)]
    approved = security.approval_gate.resolve(
        pending,
        approver="human",
        approved=True,
        reason="approved",
    )
    first = await workflow.resume(str(request.id), approved)
    phase_count = len(operations.phases)
    second = await workflow.run(str(request.id))

    assert first.status is WorkflowStatus.COMPLETED
    assert second.status is WorkflowStatus.COMPLETED
    assert len(operations.phases) == phase_count
    assert all(record.result == "success" for record in security.audit.records)
