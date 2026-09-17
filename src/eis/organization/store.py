"""Configuration-backed organizational knowledge store."""

from __future__ import annotations

from collections.abc import Iterable

from eis.organization.models import (
    OrganizationEntity,
    OrganizationEntityKind,
    OrganizationProfile,
    ProductProfile,
    Relationship,
)


class InMemoryOrganizationStore:
    """Deterministic store suitable for configuration data, tests, and local use."""

    def __init__(
        self,
        organization: OrganizationProfile,
        *,
        entities: Iterable[OrganizationEntity] = (),
        products: Iterable[ProductProfile] = (),
    ) -> None:
        self._organization = organization
        self._entities = {entity.id: entity for entity in entities}
        self._products = {product.id: product for product in products}

    def organization(self) -> OrganizationProfile:
        return self._organization

    def get_entity(self, entity_id: str) -> OrganizationEntity | None:
        return self._entities.get(entity_id)

    def get_product(self, product_id: str) -> ProductProfile | None:
        return self._products.get(product_id)

    def relationships(self, entity_id: str) -> tuple[Relationship, ...]:
        return tuple(
            relationship
            for relationship in self._organization.relationships
            if relationship.source_id == entity_id or relationship.target_id == entity_id
        )

    def retrieve(
        self,
        query: str,
        *,
        kind: OrganizationEntityKind | None = None,
        product_id: str | None = None,
    ) -> tuple[OrganizationEntity | ProductProfile, ...]:
        terms = tuple(term for term in query.casefold().split() if term)
        candidates: list[OrganizationEntity | ProductProfile]

        if product_id is not None:
            product = self._products.get(product_id)
            candidates = [product] if product is not None else []
        else:
            candidates = list(self._products.values()) + list(self._entities.values())

        results: list[OrganizationEntity | ProductProfile] = []
        for item in candidates:
            if kind is not None:
                if isinstance(item, OrganizationEntity):
                    if item.kind != kind:
                        continue
                elif kind != OrganizationEntityKind.PRODUCT:
                    continue
            searchable = self._search_text(item).casefold()
            if not terms or all(term in searchable for term in terms):
                results.append(item)
        return tuple(results)

    @staticmethod
    def _search_text(item: OrganizationEntity | ProductProfile) -> str:
        if isinstance(item, OrganizationEntity):
            return " ".join((item.id, item.name, item.description))
        return " ".join(
            (
                item.id,
                item.identity,
                item.purpose,
                item.architecture,
                *item.repositories,
                *item.technology_stack,
                *item.engineering_standards,
                *item.dependencies,
                item.current_status,
                *item.roadmap,
                *item.constraints,
            )
        )
