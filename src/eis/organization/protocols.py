"""Stable contracts for organizational intelligence storage and retrieval."""

from __future__ import annotations

from typing import Protocol

from eis.organization.models import (
    OrganizationEntity,
    OrganizationEntityKind,
    OrganizationProfile,
    ProductProfile,
    Relationship,
)


class OrganizationStore(Protocol):
    def organization(self) -> OrganizationProfile: ...

    def get_entity(self, entity_id: str) -> OrganizationEntity | None: ...

    def get_product(self, product_id: str) -> ProductProfile | None: ...

    def relationships(self, entity_id: str) -> tuple[Relationship, ...]: ...

    def retrieve(
        self,
        query: str,
        *,
        kind: OrganizationEntityKind | None = None,
        product_id: str | None = None,
    ) -> tuple[OrganizationEntity | ProductProfile, ...]: ...
