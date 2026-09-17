"""Protocols separating EIS integration contracts from external services."""

from __future__ import annotations

from typing import Protocol, Sequence

from eis.integrations.models import CIRun, Change, Document, RepositoryRef, RepositorySnapshot


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
        self, repository: RepositoryRef, title: str, body: str
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
