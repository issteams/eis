"""Local development-environment repository adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eis.integrations.models import Document, IntegrationKind, RepositoryRef, RepositorySnapshot
from eis.integrations.security import IntegrationSecurity


@dataclass(slots=True)
class LocalRepositoryConnector:
    """Read-only repository discovery and documentation ingestion for trusted local paths."""

    security: IntegrationSecurity

    async def inspect(self, repository: RepositoryRef) -> RepositorySnapshot:
        path = self._path(repository)

        async def inspect_path() -> RepositorySnapshot:
            if not path.is_dir():
                raise FileNotFoundError(path)
            files: list[str] = []
            directories: set[str] = set()
            docs: list[str] = []
            for item in path.rglob("*"):
                relative = item.relative_to(path).as_posix()
                if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in item.parts):
                    continue
                if item.is_dir():
                    directories.add(relative)
                elif item.is_file():
                    files.append(relative)
                    if self._is_documentation(relative):
                        docs.append(relative)
            return RepositorySnapshot(
                repository=repository,
                files=tuple(sorted(files)),
                directories=tuple(sorted(directories)),
                documentation=tuple(sorted(docs)),
            )

        return await self.security.read(
            str(path), operation="inspect local repository", action=inspect_path
        )

    async def ingest(self, repository: RepositoryRef) -> tuple[Document, ...]:
        path = self._path(repository)
        snapshot = await self.inspect(repository)

        async def read_docs() -> tuple[Document, ...]:
            documents: list[Document] = []
            for relative in snapshot.documentation:
                file = path / relative
                content = file.read_text(encoding="utf-8", errors="replace")
                documents.append(Document(relative, content, f"local:{file}"))
            return tuple(documents)

        return await self.security.read(
            str(path), operation="ingest local documentation", action=read_docs
        )

    @staticmethod
    def _path(repository: RepositoryRef) -> Path:
        if repository.provider is not IntegrationKind.LOCAL_REPOSITORY:
            raise ValueError("local connector requires a local repository reference")
        return Path(repository.url).expanduser().resolve()

    @staticmethod
    def _is_documentation(path: str) -> bool:
        return path.casefold().endswith((".md", ".mdx", ".rst", ".txt"))


__all__ = ["LocalRepositoryConnector"]
