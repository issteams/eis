"""Data models for Echowavs organizational intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

UNKNOWN = "UNKNOWN"


class OrganizationEntityKind(StrEnum):
    ORGANIZATION = "organization"
    DIVISION = "division"
    TEAM = "team"
    PRODUCT = "product"
    PROJECT = "project"
    REPOSITORY = "repository"
    RESPONSIBILITY = "responsibility"
    RELATIONSHIP = "relationship"
    STANDARD = "standard"
    POLICY = "policy"
    WORKFLOW = "workflow"
    OBJECTIVE = "strategic_objective"


@dataclass(frozen=True, slots=True)
class OrganizationEntity:
    """Generic organizational entity stored independently from agent logic."""

    id: str
    kind: OrganizationEntityKind
    name: str
    description: str = UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Relationship:
    """Explicit directed relationship between organizational entities."""

    source_id: str
    relation: str
    target_id: str
    description: str = UNKNOWN


@dataclass(frozen=True, slots=True)
class ProductProfile:
    """Configuration-backed profile describing a product without agent assumptions."""

    id: str
    identity: str
    purpose: str
    architecture: str = UNKNOWN
    repositories: tuple[str, ...] = ()
    technology_stack: tuple[str, ...] = ()
    engineering_standards: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    current_status: str = UNKNOWN
    roadmap: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrganizationProfile:
    """Top-level organizational configuration and knowledge graph references."""

    id: str
    name: str
    description: str = UNKNOWN
    divisions: tuple[str, ...] = ()
    teams: tuple[str, ...] = ()
    products: tuple[str, ...] = ()
    projects: tuple[str, ...] = ()
    repositories: tuple[str, ...] = ()
    responsibilities: tuple[str, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    standards: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    workflows: tuple[str, ...] = ()
    strategic_objectives: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
