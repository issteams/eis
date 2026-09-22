"""Orchestration layer for controlled external integrations."""

from __future__ import annotations

from dataclasses import dataclass

from eis.integrations.models import (
    Change,
    CIRun,
    Document,
    EngineeringRequest,
    RepositoryRef,
    RepositorySnapshot,
)
from eis.integrations.protocols import (
    CIConnector,
    DocumentationConnector,
    IssueConnector,
    RepositoryConnector,
)
from eis.security.models import Approval


@dataclass(frozen=True, slots=True)
class ProjectContext:
    repository: RepositoryRef
    snapshot: RepositorySnapshot
    documentation: tuple[Document, ...] = ()
    changes: tuple[Change, ...] = ()
    ci_runs: tuple[CIRun, ...] = ()


@dataclass(slots=True)
class IntegrationRuntime:
    """Compose external adapters without coupling EIS core to one organization."""

    repositories: RepositoryConnector
    documentation: DocumentationConnector | None = None
    ci: CIConnector | None = None
    issues: IssueConnector | None = None

    async def discover_repositories(self) -> tuple[RepositoryRef, ...]:
        return tuple(await self.repositories.discover())

    async def inspect_repository(self, repository: RepositoryRef) -> RepositorySnapshot:
        return await self.repositories.inspect(repository)

    async def project_context(
        self, repository: RepositoryRef, *, ci_limit: int = 10
    ) -> ProjectContext:
        snapshot = await self.repositories.inspect(repository)
        documentation = (
            tuple(await self.documentation.ingest(repository))
            if self.documentation is not None
            else ()
        )
        changes = tuple(await self.repositories.changes(repository))
        ci_runs = tuple(await self.ci.runs(repository, ci_limit)) if self.ci is not None else ()
        return ProjectContext(repository, snapshot, documentation, changes, ci_runs)

    async def create_engineering_task(
        self,
        repository: RepositoryRef,
        objective: str,
        constraints: tuple[str, ...] = (),
    ) -> EngineeringRequest:
        if not objective.strip():
            raise ValueError("engineering objective must not be empty")
        return EngineeringRequest(objective, repository, constraints)

    async def create_issue(
        self,
        repository: RepositoryRef,
        title: str,
        body: str,
        *,
        approval: Approval | None = None,
    ) -> str:
        if self.issues is None:
            raise RuntimeError("issue tracking integration is not configured")
        return await self.issues.create_issue(repository, title, body, approval=approval)

    async def verify(self, repository: RepositoryRef, *, limit: int = 10) -> tuple[CIRun, ...]:
        if self.ci is None:
            raise RuntimeError("CI integration is not configured")
        return tuple(await self.ci.runs(repository, limit))


__all__ = ["IntegrationRuntime", "ProjectContext"]
