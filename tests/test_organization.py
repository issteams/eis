"""Tests for organizational knowledge isolation and retrieval."""

from eis.organization import (
    CRAFTIQ,
    INITIAL_STORE,
    SMARKET,
    UNKNOWN,
    InMemoryOrganizationStore,
    OrganizationEntity,
    OrganizationEntityKind,
    OrganizationProfile,
    ProductProfile,
)


def test_initial_products_keep_unknown_fields_explicit() -> None:
    assert CRAFTIQ.current_status == UNKNOWN
    assert CRAFTIQ.architecture == UNKNOWN
    assert CRAFTIQ.engineering_standards == (UNKNOWN,)
    assert SMARKET.architecture == UNKNOWN
    assert SMARKET.technology_stack == (UNKNOWN,)


def test_product_retrieval_isolated_to_requested_product() -> None:
    results = INITIAL_STORE.retrieve("marketing", product_id="craftiq")

    assert results == (CRAFTIQ,)
    assert all(getattr(result, "id", None) == "craftiq" for result in results)


def test_product_retrieval_does_not_cross_contaminate_products() -> None:
    results = INITIAL_STORE.retrieve("fashion", product_id="craftiq")

    assert results == ()


def test_kind_filter_isolates_organizational_entities() -> None:
    results = INITIAL_STORE.retrieve(
        "repository",
        kind=OrganizationEntityKind.REPOSITORY,
    )

    assert {entity.id for entity in results} == {
        "repo-issteams-craftiq",
        "repo-issteams-eis",
        "repo-issteams-ai-marketing-engine",
    }


def test_relationship_retrieval_is_explicit() -> None:
    relationships = INITIAL_STORE.relationships("smarket")

    assert len(relationships) == 2
    assert {(item.relation, item.target_id) for item in relationships} == {
        ("part_of", "stitchai"),
        ("belongs_to", "echowavs"),
    }


def test_future_products_require_no_core_architecture_change() -> None:
    organization = OrganizationProfile(id="example", name="Example")
    future_product = ProductProfile(
        id="future-product",
        identity="Future Product",
        purpose="UNKNOWN",
    )
    store = InMemoryOrganizationStore(
        organization,
        entities=(
            OrganizationEntity(
                id="future-division",
                kind=OrganizationEntityKind.DIVISION,
                name="Future Division",
            ),
        ),
        products=(future_product,),
    )

    assert store.get_product("future-product") == future_product
    assert store.retrieve("future")[0] == future_product
