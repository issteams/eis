"""Stable contracts shared by EIS domains.

Concrete adapters belong outside these contracts so the core remains provider-agnostic.
Model operations are defined exclusively by ``eis.models``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from eis.models.interfaces import Model


@dataclass(frozen=True, slots=True)
class Evidence:
    source: str
    content: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Decision:
    conclusion: str
    rationale: str
    evidence: tuple[Evidence, ...] = ()
    uncertainty: str | None = None
    proposed_action: str | None = None


@runtime_checkable
class KnowledgeStore(Protocol):
    async def search(self, query: str, *, limit: int = 10) -> list[Evidence]: ...
    async def upsert(self, evidence: Evidence) -> None: ...


@runtime_checkable
class Repository(Protocol):
    async def read(self, path: str, *, ref: str | None = None) -> str: ...
    async def list_files(self, path: str = "", *, ref: str | None = None) -> list[str]: ...


@runtime_checkable
class Tool(Protocol):
    name: str

    async def execute(self, arguments: dict[str, Any]) -> Any: ...


@runtime_checkable
class Executor(Protocol):
    async def execute(self, action: str, *, context: dict[str, Any] | None = None) -> Any: ...


@runtime_checkable
class Evaluator(Protocol):
    async def evaluate(self, expected: Any, actual: Any) -> bool: ...


@runtime_checkable
class Agent(Protocol):
    name: str

    async def run(self, task: str, *, context: dict[str, Any] | None = None) -> Any: ...


__all__ = [
    "Agent",
    "Decision",
    "Evaluator",
    "Executor",
    "Evidence",
    "KnowledgeStore",
    "Model",
    "Repository",
    "Tool",
]
