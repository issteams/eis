from __future__ import annotations

import base64
import uuid
from pathlib import Path

import pytest

from eis.integrations import (
    IntegrationRuntime,
    IntegrationKind,
    IntegrationSecurity,
    LocalRepositoryConnector,
    RepositoryRef,
)
from eis.integrations.github import GitHubConnector
from eis.integrations.models import Change, CIRun, Document, RepositorySnapshot
from eis.security.models import Approval, ApprovalStatus, Permission, Principal, Role
from eis.security.runtime import InMemoryAuditSink, RoleAuthorizer, SecurityGateway


@pytest.fixture
def security() -> IntegrationSecurity:
    principal = Principal("integration", roles=frozenset({"reader"}))
    authorizer = RoleAuthorizer(
        roles={"reader": Role("reader", frozenset({Permission("read", "*")}))},
        principals={principal.id: principal},
    )
    return IntegrationSecurity(SecurityGateway(authorizer, InMemoryAuditSink()), principal)


@pytest.mark.anyio
async def test_local_repository_is_inspected_and_documented(
    security: IntegrationSecurity, tmp_path: Path
) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    repository = RepositoryRef(
        "demo",
        str(tmp_path),
        provider=IntegrationKind.LOCAL_REPOSITORY,
    )
    connector = LocalRepositoryConnector(security)

    snapshot = await connector.inspect(repository)
    documents = await connector.ingest(repository)

    assert "README.md" in snapshot.documentation
    assert "src/main.py" in snapshot.files
    assert documents[0].content == "# Demo\n"


@pytest.mark.anyio
async def test_local_connector_denies_unauthorized_path(tmp_path: Path) -> None:
    principal = Principal("integration", roles=frozenset({"reader"}))
    authorizer = RoleAuthorizer(
        roles={"reader": Role("reader", frozenset({Permission("read", "allowed/*")}))},
        principals={principal.id: principal},
    )
    security = IntegrationSecurity(SecurityGateway(authorizer, InMemoryAuditSink()), principal)
    repository = RepositoryRef(
        "demo",
        str(tmp_path),
        provider=IntegrationKind.LOCAL_REPOSITORY,
    )

    with pytest.raises(PermissionError):
        await LocalRepositoryConnector(security).inspect(repository)


def test_github_repository_mapping_is_provider_neutral() -> None:
    principal = Principal("integration", roles=frozenset({"reader"}))
    permissions = frozenset({Permission("read", "*"), Permission("write", "*")})
    authorizer = RoleAuthorizer(
        roles={"reader": Role("reader", permissions)},
        principals={principal.id: principal},
    )
    security = IntegrationSecurity(SecurityGateway(authorizer, InMemoryAuditSink()), principal)
    connector = GitHubConnector(security)

    repository = connector._repo_from_item(
        {
            "full_name": "example/repository",
            "html_url": "https://github.com/example/repository",
            "default_branch": "foundation/eis-architecture",
            "id": 1,
            "private": True,
        }
    )

    assert repository.name == "example/repository"
    assert repository.provider is IntegrationKind.GITHUB
    assert repository.default_branch == "foundation/eis-architecture"


def test_github_connector_rejects_untrusted_host(security: IntegrationSecurity) -> None:
    with pytest.raises(ValueError):
        GitHubConnector(security, base_url="https://example.com")


@pytest.mark.anyio
async def test_github_read_operations_are_mapped(security: IntegrationSecurity) -> None:
    repository = RepositoryRef(
        "example/repository",
        "https://github.com/example/repository",
        default_branch="main",
        provider=IntegrationKind.GITHUB,
    )

    class FakeGitHub(GitHubConnector):
        async def _get(self, path: str, *, resource: str):
            if path == "/user/repos?per_page=100":
                return [
                    {
                        "full_name": "example/repository",
                        "html_url": "https://github.com/example/repository",
                        "default_branch": "main",
                    }
                ]
            if "/git/trees/" in path:
                return {
                    "truncated": True,
                    "tree": [
                        {"path": "README.md", "type": "blob"},
                        {"path": "src", "type": "tree"},
                    ],
                }
            if "/commits?" in path:
                return [
                    {
                        "sha": "abc",
                        "html_url": "https://github.com/example/repository/commit/abc",
                        "commit": {
                            "message": "first change\nbody",
                            "author": {"name": "Example Author", "date": "2026-09-17T00:00:00Z"},
                        },
                    }
                ]
            if "/contents/README.md" in path:
                return {
                    "encoding": "base64",
                    "content": base64.b64encode(b"# EIS").decode(),
                }
            if "/actions/runs" in path:
                return {
                    "workflow_runs": [
                        {
                            "id": 7,
                            "status": "completed",
                            "conclusion": "success",
                            "html_url": "https://github.com/example/repository/actions/runs/7",
                        }
                    ]
                }
            raise AssertionError(f"unexpected path: {path}")

    connector = FakeGitHub(security)
    repositories = await connector.discover()
    snapshot = await connector.inspect(repository)
    changes = await connector.changes(repository)
    documents = await connector.ingest(repository)
    runs = await connector.runs(repository, limit=0)

    assert repositories[0].name == "example/repository"
    assert snapshot.files == ("README.md",)
    assert snapshot.directories == ("src",)
    assert snapshot.documentation == ("README.md",)
    assert snapshot.metadata["tree_truncated"] is True
    assert changes[0].summary == "first change"
    assert documents[0].content == "# EIS"
    assert runs[0].identifier == "7"


@pytest.mark.anyio
async def test_github_discover_rejects_invalid_payload(security: IntegrationSecurity) -> None:
    class FakeGitHub(GitHubConnector):
        async def _get(self, path: str, *, resource: str):
            return {"repositories": []}

    with pytest.raises(ValueError, match="not a list"):
        await FakeGitHub(security).discover()


@pytest.mark.anyio
async def test_integration_creates_tasks_without_external_side_effects(
    security: IntegrationSecurity,
) -> None:
    class Repositories:
        async def discover(self):
            return ()

        async def inspect(self, repository):
            return await LocalRepositoryConnector(security).inspect(repository)

        async def changes(self, repository):
            return ()

    integration = IntegrationRuntime(Repositories())
    repository = RepositoryRef("demo", "/tmp/demo", provider=IntegrationKind.LOCAL_REPOSITORY)
    task = await integration.create_engineering_task(repository, "inspect architecture")

    assert task.objective == "inspect architecture"
    assert task.repository == repository


@pytest.mark.anyio
async def test_integration_project_context_and_verification(security: IntegrationSecurity) -> None:
    repository = RepositoryRef("demo", "/tmp/demo", provider=IntegrationKind.LOCAL_REPOSITORY)
    snapshot = RepositorySnapshot(repository, ("README.md",), (), ("README.md",))
    change = Change("1", "update", "author", "now", "url")
    document = Document("README.md", "content", "source")
    run = CIRun("1", "completed", "success", "url")

    class Repositories:
        async def discover(self):
            return (repository,)

        async def inspect(self, target):
            return snapshot

        async def changes(self, target):
            return (change,)

    class Documentation:
        async def ingest(self, target):
            return (document,)

    class CI:
        async def runs(self, target, limit=10):
            return (run,)

    class Issues:
        async def create_issue(self, target, title, body, *, approval=None):
            return "issue-url"

    integration = IntegrationRuntime(Repositories(), Documentation(), CI(), Issues())
    assert await integration.discover_repositories() == (repository,)
    assert await integration.inspect_repository(repository) == snapshot
    context = await integration.project_context(repository, ci_limit=3)
    assert context.documentation == (document,)
    assert context.changes == (change,)
    assert context.ci_runs == (run,)
    assert await integration.create_issue(repository, "title", "body") == "issue-url"
    assert await integration.verify(repository, limit=3) == (run,)


@pytest.mark.anyio
async def test_integration_requires_configured_optional_adapters(
    security: IntegrationSecurity,
) -> None:
    repository = RepositoryRef("demo", "/tmp/demo", provider=IntegrationKind.LOCAL_REPOSITORY)
    integration = IntegrationRuntime(object())

    with pytest.raises(RuntimeError, match="issue tracking"):
        await integration.create_issue(repository, "title", "body")
    with pytest.raises(RuntimeError, match="CI integration"):
        await integration.verify(repository)
    with pytest.raises(ValueError, match="objective"):
        await integration.create_engineering_task(repository, "   ")


@pytest.mark.anyio
async def test_integration_security_records_failed_actions(security: IntegrationSecurity) -> None:
    async def fail() -> str:
        raise RuntimeError("controlled failure")

    with pytest.raises(RuntimeError, match="controlled failure"):
        await security.read("github/test", operation="read", action=fail)


@pytest.mark.anyio
async def test_external_write_requires_approval(security: IntegrationSecurity) -> None:
    called = False

    async def action() -> str:
        nonlocal called
        called = True
        return "done"

    with pytest.raises(PermissionError):
        await security.write("github/repos/demo", operation="write", action=action)
    assert not called

    approval = Approval(
        request_id=uuid.uuid4(),
        status=ApprovalStatus.APPROVED,
        approver="human",
        reason="approved test action",
    )
    result = await security.write(
        "github/repos/demo",
        operation="write",
        action=action,
        approval=approval,
    )
    assert result == "done"
    assert called


def test_github_document_path_rejects_traversal() -> None:
    assert GitHubConnector._is_safe_document_path("docs/README.md")
    assert not GitHubConnector._is_safe_document_path("docs/../secret.txt")
