"""Initial example organizational knowledge configuration.

The bundled configuration is intentionally generic and safe for public use.
Applications can replace it with their own organization-specific data.
"""

from __future__ import annotations

from eis.organization.models import (
    UNKNOWN,
    OrganizationEntity,
    OrganizationEntityKind,
    OrganizationProfile,
    ProductProfile,
)
from eis.organization.store import InMemoryOrganizationStore

EXAMPLE_ORGANIZATION = OrganizationEntity(
    id="example-organization",
    kind=OrganizationEntityKind.ORGANIZATION,
    name="Example Organization",
    description="Example organization used to demonstrate EIS organizational intelligence.",
)

EXAMPLE_PRODUCT = ProductProfile(
    id="example-product",
    identity="Example Product",
    purpose="Example application used to demonstrate EIS product-aware knowledge.",
    repositories=("example/repository",),
    current_status=UNKNOWN,
    architecture=UNKNOWN,
    technology_stack=(UNKNOWN,),
    engineering_standards=(UNKNOWN,),
    dependencies=(UNKNOWN,),
    roadmap=(UNKNOWN,),
    constraints=(UNKNOWN,),
)

EXAMPLE_REPOSITORY = OrganizationEntity(
    id="repo-example-repository",
    kind=OrganizationEntityKind.REPOSITORY,
    name="example/repository",
    description="Example repository used by the bundled organization configuration.",
    metadata={"repository": "example/repository"},
)

ORGANIZATION = OrganizationProfile(
    id="example-organization",
    name="Example Organization",
    description=EXAMPLE_ORGANIZATION.description,
    products=("example-product",),
    repositories=(EXAMPLE_REPOSITORY.id,),
    relationships=(),
    divisions=(UNKNOWN,),
    teams=(UNKNOWN,),
    projects=(UNKNOWN,),
    responsibilities=(UNKNOWN,),
    standards=(UNKNOWN,),
    policies=(UNKNOWN,),
    workflows=(UNKNOWN,),
    strategic_objectives=(UNKNOWN,),
)

INITIAL_STORE = InMemoryOrganizationStore(
    ORGANIZATION,
    entities=(EXAMPLE_ORGANIZATION, EXAMPLE_REPOSITORY),
    products=(EXAMPLE_PRODUCT,),
)

__all__ = [
    "EXAMPLE_ORGANIZATION",
    "EXAMPLE_PRODUCT",
    "EXAMPLE_REPOSITORY",
    "INITIAL_STORE",
    "ORGANIZATION",
    "UNKNOWN",
]
