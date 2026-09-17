"""Security, governance, approval, and audit tests."""

from uuid import uuid4

import pytest

from eis.security import (
    ActionRequest,
    ActionType,
    AgentIdentity,
    ApprovalRequest,
    AuthorizationError,
    AuthorizationStatus,
    EnvironmentSecretProvider,
    GovernanceGuard,
    GovernanceLimitError,
    GovernanceLimits,
    InMemoryApprovalGate,
    InMemoryAuditSink,
    Permission,
    Principal,
    RedactingProtector,
    ResourceRestriction,
    RiskLevel,
    Role,
    RoleAuthorizer,
    SecurityGateway,
)


def make_gateway() -> SecurityGateway:
    principal = Principal("human", frozenset({"developer"}))
    role = Role(
        "developer",
        frozenset(
            {
                Permission("read", "repo:*"),
                Permission("write", "repo:craftiq"),
            }
        ),
    )
    authorizer = RoleAuthorizer(
        roles={"developer": role},
        principals={"human": principal},
        restrictions=(ResourceRestriction("repo:production", frozenset({"read"})),),
    )
    return SecurityGateway(authorizer, InMemoryAuditSink())


def test_rbac_allows_granted_resource_and_denies_unknown() -> None:
    gateway = make_gateway()
    request = ActionRequest(
        Principal("human", frozenset({"developer"})), "write", "repo:craftiq"
    )
    assert gateway.authorize(request).status is AuthorizationStatus.ALLOWED
    unknown = ActionRequest(
        Principal("unknown", frozenset({"missing"})), "write", "repo:craftiq"
    )
    assert gateway.authorize(unknown).status is AuthorizationStatus.DENIED


def test_resource_restriction_fails_closed() -> None:
    gateway = make_gateway()
    request = ActionRequest(
        Principal("human", frozenset({"developer"})), "write", "repo:production"
    )
    with pytest.raises(AuthorizationError):
        gateway.check(request)


def test_high_risk_actions_require_human_approval() -> None:
    gateway = make_gateway()
    task_id = uuid4()
    request = ActionRequest(
        Principal("human", frozenset({"developer"})),
        ActionType.DEPLOY,
        "production",
        RiskLevel.CRITICAL,
        task_id=task_id,
    )
    with pytest.raises(AuthorizationError):
        gateway.execute_approved(request)
    pending = gateway.approval_gate.request(
        ApprovalRequest(
            "production_deploy", "production", "human", "release", RiskLevel.CRITICAL, task_id
        )
    )
    approved = gateway.approval_gate.resolve(
        pending,
        approver="owner",
        approved=True,
        reason="reviewed deployment",
    )
    gateway.execute_approved(request, approval=approved)
    assert gateway.audit.records[-1].authorization is AuthorizationStatus.ALLOWED


def test_audit_redacts_sensitive_values() -> None:
    gateway = make_gateway()
    request = ActionRequest(
        Principal("human", frozenset({"developer"})),
        "read",
        "repo:craftiq",
        target="Authorization: Bearer super-secret-token",
    )
    gateway.execute_approved(request, result="success", failure="token=hidden-secret")
    record = gateway.audit.records[-1]
    assert "super-secret-token" not in str(record.target)
    assert "hidden-secret" not in str(record.failure)


def test_secret_provider_reads_without_persisting() -> None:
    import os

    os.environ["EIS_TEST_SECRET"] = "value"
    try:
        assert EnvironmentSecretProvider(prefix="EIS_").get("TEST_SECRET") == "value"
    finally:
        del os.environ["EIS_TEST_SECRET"]


def test_redactor_handles_nested_values() -> None:
    redacted = RedactingProtector().redact({"token": "secret-value", "items": ["Bearer abc"]})
    assert "secret-value" not in str(redacted)
    assert "abc" not in str(redacted)


def test_governance_enforces_rate_and_cost_limits() -> None:
    guard = GovernanceGuard(GovernanceLimits(max_actions_per_window=1, max_cost=1.0))
    request = ActionRequest(Principal("human"), "read", "repo", estimated_cost=1.0)
    guard.check(request)
    guard.commit(request, 1.0, 0.0)
    with pytest.raises(GovernanceLimitError):
        guard.check(request)


def test_agent_permissions_can_be_added_to_role_permissions() -> None:
    gateway = make_gateway()
    agent = AgentIdentity(uuid4(), "research", frozenset({Permission("read", "docs:*")}))
    request = ActionRequest(
        Principal("human", frozenset({"developer"})),
        "read",
        "docs:one",
        agent=agent,
    )
    assert gateway.authorize(request).status is AuthorizationStatus.ALLOWED


def test_approval_gate_requires_identified_human() -> None:
    gate = InMemoryApprovalGate()
    approval = gate.request(
        ApprovalRequest("delete_file", "repo:x", "agent", "cleanup", RiskLevel.HIGH)
    )
    with pytest.raises(AuthorizationError):
        gate.resolve(approval, approver="", approved=True, reason="")
