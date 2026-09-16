"""Stable identity primitives used across the EIS runtime."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Identity:
    """An immutable, globally unique identity with a human-readable name."""

    id: UUID
    name: str

    @classmethod
    def create(cls, name: str) -> "Identity":
        if not name.strip():
            raise ValueError("identity name must not be empty")
        return cls(id=uuid4(), name=name.strip())


@dataclass(frozen=True, slots=True)
class EISIdentity(Identity):
    """Identity of the EIS runtime instance."""


@dataclass(frozen=True, slots=True)
class CompanyIdentity(Identity):
    """Identity of an organization known to EIS."""


@dataclass(frozen=True, slots=True)
class ProductIdentity(Identity):
    """Identity of a product belonging to an organization."""


@dataclass(frozen=True, slots=True)
class DivisionIdentity(Identity):
    """Identity of an organizational division."""


@dataclass(frozen=True, slots=True)
class ProjectIdentity(Identity):
    """Identity of a project belonging to a product."""


@dataclass(frozen=True, slots=True)
class RepositoryIdentity(Identity):
    """Identity of a source repository belonging to a project."""


@dataclass(frozen=True, slots=True)
class TaskIdentity(Identity):
    """Identity of a unit of work."""


@dataclass(frozen=True, slots=True)
class SessionIdentity(Identity):
    """Identity of a runtime interaction session."""


@dataclass(frozen=True, slots=True)
class RequestIdentity(Identity):
    """Identity of an individual request within a session."""

    @classmethod
    def create(cls, name: str = "request") -> "RequestIdentity":
        return cls(id=uuid4(), name=name.strip() or "request")


@dataclass(frozen=True, slots=True)
class CorrelationId:
    """Identifier used to correlate events across a single operation."""

    value: UUID

    @classmethod
    def create(cls) -> "CorrelationId":
        return cls(value=uuid4())

    def __str__(self) -> str:
        return str(self.value)
