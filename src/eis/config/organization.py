"""Configuration models for organization-defined EIS identity."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NamedConfig(BaseModel):
    """A validated organization-defined named entity."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(min_length=1)


class ProjectConfig(NamedConfig):
    """Project configuration nested under a product."""


class ProductConfig(NamedConfig):
    """Product configuration nested under an organization/division."""

    projects: tuple[ProjectConfig, ...] = ()


class DivisionConfig(NamedConfig):
    """Division configuration nested under a company."""

    products: tuple[ProductConfig, ...] = ()


class CompanyConfig(NamedConfig):
    """Organization identity and its configured hierarchy."""

    divisions: tuple[DivisionConfig, ...] = ()
