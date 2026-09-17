"""GitHub adapter implemented behind the EIS integration contracts."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from eis.integrations.models import (
    CIRun,
    Change,
    Document,
    IntegrationKind,
    RepositoryRef,
    RepositorySnapshot,
)
from eis.integrations.security import IntegrationSecurity


@dataclass(slots=True)
class GitHubConnector:
    """Controlled GitHub REST adapter; no GitHub concepts leak into EIS core."""

    security: IntegrationSecurity
    token: str | None = None
    base_url: str = "https://api.github.com"
    timeout: float = 20.0

    def _client(self) -> httpx.AsyncClient:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=self.timeout)

    async def _get(self, path: str, *, resource: str) -> Any:
        async def request() -> Any:
            async with self._client() as client:
                response = await client.get(path)
                response.raise_for_status()
                return response.json()

        return await self.security.read(
            resource,
            operation=f"github GET {path}",
            action=request,
        )

    @staticmethod
    def _repo_from_item(item: dict[str, Any]) -> RepositoryRef:
        return RepositoryRef(
            name=str(item["full_name"]),
            url=str(item["html_url"]),
            default_branch=str(item.get("default_branch") or "main"),
            provider=IntegrationKind.GITHUB,
            metadata={"id": item.get("id"), "private": item.get("private", False)},
        )

    async def discover(self) -> tuple[RepositoryRef, ...]:
        data = await self._get("/user/repos?per_page=100", resource="github/repositories")
        if not isinstance(data, list):
            raise ValueError("GitHub repository response was not a list")
        return tuple(self._repo_from_item(item) for item in data if isinstance(item, dict))

    async def inspect(self, repository: RepositoryRef) -> RepositorySnapshot:
        owner, name = repository.name.split("/", 1)
        data = await self._get(
            f"/repos/{owner}/{name}/git/trees/{repository.default_branch}?recursive=1",
            resource=f"github/repos/{repository.name}",
        )
        entries = data.get("tree", [])
        files = tuple(
            str(item["path"])
            for item in entries
            if item.get("type") == "blob" and isinstance(item.get("path"), str)
        )
        directories = tuple(
            str(item["path"])
            for item in entries
            if item.get("type") == "tree" and isinstance(item.get("path"), str)
        )
        docs = tuple(path for path in files if self._is_documentation(path))
        return RepositorySnapshot(
            repository=repository,
            files=files,
            directories=directories,
            documentation=docs,
            metadata={"tree_truncated": bool(data.get("truncated", False))},
        )

    async def changes(self, repository: RepositoryRef) -> tuple[Change, ...]:
        owner, name = repository.name.split("/", 1)
        data = await self._get(
            f"/repos/{owner}/{name}/commits?per_page=20",
            resource=f"github/repos/{repository.name}/commits",
        )
        return tuple(
            Change(
                identifier=str(item["sha"]),
                summary=str(item.get("commit", {}).get("message", "")).splitlines()[0],
                author=str(item.get("commit", {}).get("author", {}).get("name", "unknown")),
                timestamp=str(item.get("commit", {}).get("author", {}).get("date", "")),
                url=str(item.get("html_url", "")),
            )
            for item in data
            if isinstance(item, dict)
        )

    async def ingest(self, repository: RepositoryRef) -> tuple[Document, ...]:
        snapshot = await self.inspect(repository)
        documents: list[Document] = []
        for path in snapshot.documentation:
            if not self._is_safe_document_path(path):
                continue
            owner, name = repository.name.split("/", 1)
            encoded = await self._get(
                f"/repos/{owner}/{name}/contents/{path}",
                resource=f"github/repos/{repository.name}/docs",
            )
            if encoded.get("encoding") != "base64" or not encoded.get("content"):
                continue
            content = base64.b64decode(encoded["content"]).decode("utf-8", errors="replace")
            documents.append(Document(path, content, f"github:{repository.name}:{path}"))
        return tuple(documents)

    async def runs(self, repository: RepositoryRef, limit: int = 10) -> tuple[CIRun, ...]:
        owner, name = repository.name.split("/", 1)
        data = await self._get(
            f"/repos/{owner}/{name}/actions/runs?per_page={max(1, min(limit, 100))}",
            resource=f"github/repos/{repository.name}/actions",
        )
        return tuple(
            CIRun(
                identifier=str(item["id"]),
                status=str(item.get("status", "unknown")),
                conclusion=item.get("conclusion"),
                url=str(item.get("html_url", "")),
            )
            for item in data.get("workflow_runs", [])
        )

    async def create_issue(
        self,
        repository: RepositoryRef,
        title: str,
        body: str,
        *,
        approval=None,
    ) -> str:
        owner, name = repository.name.split("/", 1)

        async def create() -> str:
            async with self._client() as client:
                response = await client.post(
                    f"/repos/{owner}/{name}/issues",
                    json={"title": title, "body": body},
                )
                response.raise_for_status()
                return str(response.json()["html_url"])

        return await self.security.write(
            f"github/repos/{repository.name}/issues",
            operation="github create issue",
            action=create,
            approval=approval,
        )

    @staticmethod
    def _is_documentation(path: str) -> bool:
        lower = path.casefold()
        return lower.endswith((".md", ".mdx", ".rst", ".txt")) or lower.startswith("docs/")

    @staticmethod
    def _is_safe_document_path(path: str) -> bool:
        return not any(part in {".", ".."} for part in path.split("/"))


__all__ = ["GitHubConnector"]
