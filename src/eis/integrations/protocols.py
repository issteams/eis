"""Protocols separating EIS integration contracts from external services."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from eis.integrations.models import Change, CIRun, Document, RepositoryRef, RepositorySnapshot
from eis.security.models import Approval


class RepositoryConnector(Protocol):
    async def discover(self) -> Sequence[RepositoryRef]: ...

    async def inspect(self, repository: RepositoryRef) -> RepositorySnapshot: ...

    async def changes(self, repository: RepositoryRef) -> Sequence[Change]: ...


class DocumentationConnector(Protocol):
    async def ingest(self, repository: RepositoryRef) -> Sequence[Document]: ...


class CIConnector(Protocol):
    async def runs(self, repository: RepositoryRef, limit: int = 10) -> Sequence[CIRun]: ...


class IssueConnector(Protocol):
    async def create_issue(
        self,
        repository: RepositoryRef,
        title: str,
        body: str,
        *,
        approval: Approval | None = None,
    ) -> str: ...


class IntegrationExecutor(Protocol):
    async def execute_approved(
        self, operation: str, resource: str, payload: object = None
    ) -> object: ...


__all__ = [
    "CIConnector",
    "DocumentationConnector",
    "IntegrationExecutor",
    "IssueConnector",
    "RepositoryConnector",
]
