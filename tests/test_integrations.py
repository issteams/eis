from __future__ import annotations

from pathlib import Path

import pytest

from eis.integrations import (
    EchowavsIntegration,
    IntegrationKind,
    IntegrationSecurity,
    LocalRepositoryConnector,
    RepositoryRef,
)
from eis.integrations.github import GitHubConnector
from eis.security.models import Permission, Principal, Role
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
    authorizer = RoleAuthorizer(
        roles={"reader": Role("reader", frozenset({Permission("read", "*"), Permission("write", "*")}))},
        principals={principal.id: principal},
    )
    security = IntegrationSecurity(SecurityGateway(authorizer, InMemoryAuditSink()), principal)
    connector = GitHubConnector(security)

    repository = connector._repo_from_item(
        {
            "full_name": "issteams/eis",
            "html_url": "https://github.com/issteams/eis",
            "default_branch": "foundation/eis-architecture",
            "id": 1,
            "private": True,
        }
    )

    assert repository.name == "issteams/eis"
    assert repository.provider is IntegrationKind.GITHUB
    assert repository.default_branch == "foundation/eis-architecture"


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

    integration = EchowavsIntegration(Repositories())
    repository = RepositoryRef("demo", "/tmp/demo", provider=IntegrationKind.LOCAL_REPOSITORY)
    task = await integration.create_engineering_task(repository, "inspect architecture")

    assert task.objective == "inspect architecture"
    assert task.repository == repository


def test_github_document_path_rejects_traversal() -> None:
    assert GitHubConnector._is_safe_document_path("docs/README.md")
    assert not GitHubConnector._is_safe_document_path("docs/../secret.txt")
