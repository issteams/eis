"""Stable models for controlled external system integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class IntegrationKind(StrEnum):
    GITHUB = "github"
    LOCAL_REPOSITORY = "local_repository"
    DOCUMENTATION = "documentation"
    CI = "ci"
    ISSUE_TRACKING = "issue_tracking"
    INTERNAL_API = "internal_api"


@dataclass(frozen=True, slots=True)
class RepositoryRef:
    name: str
    url: str
    default_branch: str = "main"
    provider: IntegrationKind = IntegrationKind.GITHUB
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    repository: RepositoryRef
    files: tuple[str, ...] = ()
    directories: tuple[str, ...] = ()
    documentation: tuple[str, ...] = ()
    recent_changes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Document:
    title: str
    content: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class Change:
    identifier: str
    summary: str
    author: str
    timestamp: str
    url: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CIRun:
    identifier: str
    status: str
    conclusion: str | None
    url: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineeringRequest:
    objective: str
    repository: RepositoryRef
    constraints: tuple[str, ...] = ()
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    operation: str
    success: bool
    value: Any = None
    error: str | None = None
    audit_id: UUID | None = None


__all__ = [
    "CIRun",
    "Change",
    "Document",
    "EngineeringRequest",
    "IntegrationKind",
    "IntegrationResult",
    "RepositoryRef",
    "RepositorySnapshot",
]
