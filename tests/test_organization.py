"""Tests for organizational knowledge isolation and retrieval."""

from eis.organization import (
    EXAMPLE_ORGANIZATION,
    EXAMPLE_PRODUCT,
    EXAMPLE_REPOSITORY,
    INITIAL_STORE,
    UNKNOWN,
    InMemoryOrganizationStore,
    OrganizationEntity,
    OrganizationEntityKind,
    OrganizationProfile,
    ProductProfile,
)


def test_initial_products_keep_unknown_fields_explicit() -> None:
    assert EXAMPLE_PRODUCT.current_status == UNKNOWN
    assert EXAMPLE_PRODUCT.architecture == UNKNOWN
    assert EXAMPLE_PRODUCT.engineering_standards == (UNKNOWN,)
    assert EXAMPLE_PRODUCT.technology_stack == (UNKNOWN,)


def test_product_retrieval_isolated_to_requested_product() -> None:
    results = INITIAL_STORE.retrieve("application", product_id="example-product")

    assert results == (EXAMPLE_PRODUCT,)
    assert all(getattr(result, "id", None) == "example-product" for result in results)


def test_product_retrieval_does_not_cross_contaminate_products() -> None:
    results = INITIAL_STORE.retrieve("fashion", product_id="example-product")

    assert results == ()


def test_kind_filter_isolates_organizational_entities() -> None:
    results = INITIAL_STORE.retrieve(
        "repository",
        kind=OrganizationEntityKind.REPOSITORY,
    )

    assert results == (EXAMPLE_REPOSITORY,)


def test_product_kind_filter_retrieves_only_products() -> None:
    results = INITIAL_STORE.retrieve("", kind=OrganizationEntityKind.PRODUCT)

    assert results == (EXAMPLE_PRODUCT,)


def test_relationship_retrieval_is_explicit() -> None:
    relationships = INITIAL_STORE.relationships("example-product")

    assert relationships == ()


def test_store_accessors_return_known_and_unknown_entities() -> None:
    assert INITIAL_STORE.organization().name == EXAMPLE_ORGANIZATION.name
    assert INITIAL_STORE.get_entity("example-organization") == EXAMPLE_ORGANIZATION
    assert INITIAL_STORE.get_entity("missing") is None
    assert INITIAL_STORE.get_product("missing") is None


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
