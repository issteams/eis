"""Initial Echowavs organizational knowledge configuration.

Only facts established by the current EIS knowledge base are populated. Missing
organizational information remains explicitly represented as ``UNKNOWN``.
"""

from __future__ import annotations

from eis.organization.models import (
    UNKNOWN,
    OrganizationEntity,
    OrganizationEntityKind,
    OrganizationProfile,
    ProductProfile,
    Relationship,
)
from eis.organization.store import InMemoryOrganizationStore

ECHOWAVS = OrganizationEntity(
    id="echowavs",
    kind=OrganizationEntityKind.ORGANIZATION,
    name="Echowavs",
    description=(
        "Technology company providing innovative software solutions for business "
        "efficiency and growth."
    ),
)

CRAFTIQ = ProductProfile(
    id="craftiq",
    identity="CraftIQ",
    purpose="AI marketing platform intended to make marketing easier for businesses.",
    repositories=("issteams/craftiq",),
    current_status=UNKNOWN,
    architecture=UNKNOWN,
    technology_stack=("React", "TypeScript", "Tailwind CSS", "Django", "Python"),
    engineering_standards=(UNKNOWN,),
    dependencies=("ai-marketing-engine",),
    roadmap=("UNKNOWN",),
    constraints=(UNKNOWN,),
)

STITCHAI = ProductProfile(
    id="stitchai",
    identity="StitchAI",
    purpose="Product family for tailoring and fashion-related software experiences.",
    current_status=UNKNOWN,
    architecture=UNKNOWN,
    technology_stack=(UNKNOWN,),
    engineering_standards=(UNKNOWN,),
    dependencies=(UNKNOWN,),
    roadmap=(UNKNOWN,),
    constraints=(UNKNOWN,),
)

SMARKET = ProductProfile(
    id="smarket",
    identity="SMarket",
    purpose=(
        "Fashion and accessories marketplace where sellers can publish products "
        "and buyers can discover them."
    ),
    current_status=UNKNOWN,
    architecture=UNKNOWN,
    technology_stack=(UNKNOWN,),
    engineering_standards=(UNKNOWN,),
    dependencies=(UNKNOWN,),
    roadmap=(UNKNOWN,),
    constraints=(UNKNOWN,),
)

EIS = ProductProfile(
    id="eis",
    identity="EIS",
    purpose=(
        "Echowavs Intelligent System providing organizational, knowledge, agent, "
        "engineering, and verification intelligence."
    ),
    repositories=("issteams/eis",),
    current_status="development",
    architecture=(
        "modular Python package with shared knowledge, context, agent, tool, "
        "engineering, verification, and specialized-agent layers."
    ),
    technology_stack=("Python",),
    engineering_standards=(
        "production-oriented modular architecture",
        "verification before success reporting",
    ),
    dependencies=(),
    roadmap=("UNKNOWN",),
    constraints=("organizational facts must come from the data layer",),
)

REPOSITORIES = (
    OrganizationEntity(
        id="repo-issteams-craftiq",
        kind=OrganizationEntityKind.REPOSITORY,
        name="issteams/craftiq",
        description="CraftIQ repository.",
        metadata={"repository": "issteams/craftiq"},
    ),
    OrganizationEntity(
        id="repo-issteams-eis",
        kind=OrganizationEntityKind.REPOSITORY,
        name="issteams/eis",
        description="EIS repository.",
        metadata={"repository": "issteams/eis"},
    ),
    OrganizationEntity(
        id="repo-issteams-ai-marketing-engine",
        kind=OrganizationEntityKind.REPOSITORY,
        name="issteams/ai_marketing_engine",
        description="AI marketing engine repository.",
        metadata={"repository": "issteams/ai_marketing_engine"},
    ),
)

RELATIONSHIPS = (
    Relationship("craftiq", "belongs_to", "echowavs"),
    Relationship("stitchai", "belongs_to", "echowavs"),
    Relationship("smarket", "part_of", "stitchai"),
    Relationship("smarket", "belongs_to", "echowavs"),
    Relationship("eis", "belongs_to", "echowavs"),
    Relationship("craftiq", "uses", "repo-issteams-craftiq"),
    Relationship("eis", "uses", "repo-issteams-eis"),
    Relationship("craftiq", "depends_on", "repo-issteams-ai-marketing-engine"),
)

ORGANIZATION = OrganizationProfile(
    id="echowavs",
    name="Echowavs",
    description=ECHOWAVS.description,
    products=("craftiq", "stitchai", "smarket", "eis"),
    repositories=tuple(repository.id for repository in REPOSITORIES),
    relationships=RELATIONSHIPS,
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
    entities=(ECHOWAVS, *REPOSITORIES),
    products=(CRAFTIQ, STITCHAI, SMARKET, EIS),
)

__all__ = [
    "CRAFTIQ",
    "ECHOWAVS",
    "EIS",
    "INITIAL_STORE",
    "ORGANIZATION",
    "RELATIONSHIPS",
    "REPOSITORIES",
    "SMARKET",
    "STITCHAI",
    "UNKNOWN",
]
