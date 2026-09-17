from __future__ import annotations

import asyncio

import pytest

from eis.redteam import (
    AttackCategory,
    AttackObservation,
    RedTeamFramework,
    builtin_cases,
)
from eis.security.models import ActionRequest, Permission, Principal, RiskLevel, Role
from eis.security.runtime import (
    AuthorizationError,
    InMemoryAuditSink,
    RoleAuthorizer,
    SecurityGateway,
)


def test_builtin_suite_covers_required_attack_categories() -> None:
    cases = builtin_cases()
    categories = {case.category for case in cases}

    assert len(cases) == 18
    assert categories == set(AttackCategory)


def test_redteam_finds_unsafe_behavior() -> None:
    case = builtin_cases()[0]

    def vulnerable_target(case):
        return AttackObservation(
            case_id=case.id,
            blocked=False,
            honest=False,
            failure_concealed=True,
        )

    report = asyncio.run(RedTeamFramework().run((case,), vulnerable_target))

    assert report.total_cases == 1
    assert report.safe == 0
    assert len(report.unresolved_findings) == 1
    assert not report.passes_release_gate


def test_safe_target_passes_release_gate() -> None:
    def safe_target(case):
        return AttackObservation(
            case_id=case.id,
            blocked=True,
            honest=True,
        )

    report = asyncio.run(RedTeamFramework().run(builtin_cases(), safe_target))

    assert report.total_cases == 18
    assert report.block_rate == 1.0
    assert report.safety_rate == 1.0
    assert report.passes_release_gate
    assert report.unresolved_findings == ()


def test_security_gateway_denies_permission_escalation() -> None:
    principal = Principal("agent", roles=frozenset({"reader"}))
    authorizer = RoleAuthorizer(
        roles={
            "reader": Role("reader", frozenset({Permission("read", "repo/*")})),
        },
        principals={principal.id: principal},
    )
    gateway = SecurityGateway(authorizer, InMemoryAuditSink())

    with pytest.raises(AuthorizationError):
        gateway.check(ActionRequest(principal, "write", "repo/main.py"))


def test_security_gateway_requires_approval_for_destructive_action() -> None:
    principal = Principal("operator")
    authorizer = RoleAuthorizer(
        roles={"operator": Role("operator", frozenset({Permission("delete", "repo/*")}))},
        principals={principal.id: principal},
    )
    gateway = SecurityGateway(authorizer, InMemoryAuditSink())

    request = ActionRequest(
        principal,
        "delete_repository",
        "repo/production",
        risk_level=RiskLevel.CRITICAL,
    )

    with pytest.raises(AuthorizationError):
        gateway.execute_approved(request)


def test_security_gateway_redacts_secrets_in_audit() -> None:
    principal = Principal("operator")
    authorizer = RoleAuthorizer(
        roles={"operator": Role("operator", frozenset({Permission("read", "repo/*")}))},
        principals={principal.id: principal},
    )
    audit = InMemoryAuditSink()
    gateway = SecurityGateway(authorizer, audit)

    gateway.execute_approved(
        ActionRequest(
            principal,
            "read",
            "repo/main.py",
            target="authorization=super-secret-value",
        )
    )

    assert audit.records
    record = audit.records[-1]
    assert "super-secret-value" not in (record.target or "")
