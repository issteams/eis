"""Organizational and engineering hierarchy understood by EIS."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from eis.core.identity import (
    CompanyIdentity,
    DivisionIdentity,
    ProductIdentity,
    ProjectIdentity,
    RepositoryIdentity,
    TaskIdentity,
)


@dataclass(frozen=True, slots=True)
class OrganizationHierarchy:
    """Immutable scope from organization through the current task."""

    company: CompanyIdentity
    division: DivisionIdentity | None = None
    product: ProductIdentity | None = None
    project: ProjectIdentity | None = None
    repository: RepositoryIdentity | None = None
    task: TaskIdentity | None = None

    def ids(self) -> tuple[UUID, ...]:
        """Return populated hierarchy identifiers from broadest to narrowest."""
        identities = (
            self.company,
            self.division,
            self.product,
            self.project,
            self.repository,
            self.task,
        )
        return tuple(identity.id for identity in identities if identity is not None)

    def scope(self) -> str:
        """Return the populated hierarchy as a stable human-readable path."""
        identities = (
            self.company,
            self.division,
            self.product,
            self.project,
            self.repository,
            self.task,
        )
        return " / ".join(identity.name for identity in identities if identity is not None)
