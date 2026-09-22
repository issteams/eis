"""Controlled adapters for integrating EIS with external systems."""

from eis.integrations.github import GitHubConnector
from eis.integrations.local import LocalRepositoryConnector
from eis.integrations.models import (
    Change,
    CIRun,
    Document,
    EngineeringRequest,
    IntegrationKind,
    IntegrationResult,
    RepositoryRef,
    RepositorySnapshot,
)
from eis.integrations.runtime import IntegrationRuntime, ProjectContext
from eis.integrations.security import IntegrationSecurity

__all__ = [
    "CIRun",
    "Change",
    "Document",
    "EngineeringRequest",
    "GitHubConnector",
    "IntegrationKind",
    "IntegrationResult",
    "IntegrationRuntime",
    "IntegrationSecurity",
    "LocalRepositoryConnector",
    "ProjectContext",
    "RepositoryRef",
    "RepositorySnapshot",
]
