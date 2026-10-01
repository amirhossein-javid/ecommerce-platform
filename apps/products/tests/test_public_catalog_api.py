from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Category, Product, ProductImage


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def categories(db):
    parent = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Laptops", parent=parent)
    inactive = Category.objects.create(name="Hidden", is_active=False)
    return parent, child, inactive


def create_product(
    category,
    slug,
    *,
    name=None,
    sku=None,
    description="",
    price="100.00",
    stock_quantity=0,
    status_value=Product.Status.ACTIVE,
):
    return Product.objects.create(
        category=category,
        name=name or slug.replace("-", " ").title(),
        slug=slug,
        sku=sku or slug.upper(),
        description=description,
        price=Decimal(price),
        stock_quantity=stock_quantity,
        status=status_value,
    )


def create_image(product, position, *, is_primary=False, alt_text=""):
    return ProductImage.objects.create(
        product=product,
        image=f"products/{product.pk}/image-{position}.jpg",
        alt_text=alt_text,
        position=position,
        is_primary=is_primary,
    )


@pytest.mark.django_db
def test_category_list_exposes_only_active_flat_categories(api_client, categories):
    parent, child, inactive = categories

    response = api_client.get(reverse("products:category-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": parent.pk,
            "name": "Electronics",
            "slug": "electronics",
            "parent": None,
        },
        {
            "id": child.pk,
            "name": "Laptops",
            "slug": "laptops",
            "parent": {
                "id": parent.pk,
                "name": "Electronics",
                "slug": "electronics",
            },
        },
    ]
    assert inactive.slug not in {item["slug"] for item in response.json()}
    assert "children" not in response.json()[0]


@pytest.mark.django_db
def test_category_detail_visibility(api_client, categories):
    parent, _, inactive = categories

    active_response = api_client.get(
        reverse("products:category-detail", kwargs={"slug": parent.slug})
    )
    inactive_response = api_client.get(
        reverse("products:category-detail", kwargs={"slug": inactive.slug})
    )

    assert active_response.status_code == status.HTTP_200_OK
    assert active_response.json()["slug"] == parent.slug
    assert inactive_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_inactive_parent_is_not_exposed_in_category_response(api_client):
    parent = Category.objects.create(name="Hidden Parent", is_active=False)
    child = Category.objects.create(name="Visible Child", parent=parent)

    response = api_client.get(
        reverse("products:category-detail", kwargs={"slug": child.slug})
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["parent"] is None


@pytest.mark.django_db
def test_product_list_and_detail_expose_only_active_products(api_client, categories):
    category, _, _ = categories
    active = create_product(category, "active-product")
    draft = create_product(
        category,
        "draft-product",
        status_value=Product.Status.DRAFT,
    )
    archived = create_product(
        category,
        "archived-product",
        status_value=Product.Status.ARCHIVED,
    )

    list_response = api_client.get(reverse("products:product-list"))

    assert list_response.status_code == status.HTTP_200_OK
    assert [item["slug"] for item in list_response.json()["results"]] == [active.slug]
    for hidden in (draft, archived):
        detail_response = api_client.get(
            reverse("products:product-detail", kwargs={"slug": hidden.slug})
        )
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_active_product_in_inactive_category_is_not_public(api_client, categories):
    active_category, _, inactive_category = categories
    visible = create_product(active_category, "visible-product")
    hidden = create_product(inactive_category, "hidden-by-category")

    list_response = api_client.get(reverse("products:product-list"))
    hidden_detail_response = api_client.get(
        reverse("products:product-detail", kwargs={"slug": hidden.slug})
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert [item["slug"] for item in list_response.json()["results"]] == [visible.slug]
    assert hidden_detail_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_product_visibility_does_not_check_category_ancestors(api_client):
    inactive_parent = Category.objects.create(name="Inactive Parent", is_active=False)
    active_category = Category.objects.create(
        name="Active Child",
        parent=inactive_parent,
    )
    product = create_product(active_category, "visible-through-active-category")

    list_response = api_client.get(reverse("products:product-list"))
    detail_response = api_client.get(
        reverse("products:product-detail", kwargs={"slug": product.slug})
    )

    assert [item["slug"] for item in list_response.json()["results"]] == [product.slug]
    assert detail_response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_product_list_is_lightweight_and_hides_internal_fields(api_client, categories):
    category, _, _ = categories
    product = create_product(
        category,
        "gaming-laptop",
        description="Powerful gaming machine",
        stock_quantity=4,
    )
    image = create_image(product, 0, alt_text="Front view")

    response = api_client.get(reverse("products:product-list"))

    assert response.status_code == status.HTTP_200_OK
    item = response.json()["results"][0]
    assert set(item) == {
        "id",
        "name",
        "slug",
        "category",
        "price",
        "in_stock",
        "primary_image",
    }
    assert item["in_stock"] is True
    assert item["category"] == {
        "id": category.pk,
        "name": category.name,
        "slug": category.slug,
    }
    assert item["primary_image"] == {
        "id": image.pk,
        "image": f"http://testserver/media/{image.image.name}",
        "alt_text": "Front view",
        "is_primary": True,
        "position": 0,
    }
    assert "sku" not in item
    assert "stock_quantity" not in item
    assert "description" not in item


@pytest.mark.django_db
def test_product_list_uses_null_for_missing_primary_image(api_client, categories):
    category, _, _ = categories
    create_product(category, "product-without-image")

    response = api_client.get(reverse("products:product-list"))

    assert response.json()["results"][0]["primary_image"] is None


@pytest.mark.django_db
def test_product_detail_includes_description_and_ordered_images(
    api_client,
    categories,
    django_assert_num_queries,
):
    category, _, _ = categories
    product = create_product(
        category,
        "gaming-laptop",
        description="Powerful gaming machine",
        stock_quantity=0,
    )
    last = create_image(product, 5, alt_text="Back view")
    first = create_image(product, 1, alt_text="Front view")

    with django_assert_num_queries(2):
        response = api_client.get(
            reverse("products:product-detail", kwargs={"slug": product.slug})
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["description"] == "Powerful gaming machine"
    assert data["in_stock"] is False
    assert [image["id"] for image in data["images"]] == [first.pk, last.pk]
    assert "primary_image" not in data
    assert "sku" not in data
    assert "stock_quantity" not in data
    assert "created_at" not in data
    assert "updated_at" not in data


@pytest.mark.django_db
def test_product_list_filters_by_category_slug(api_client, categories):
    parent, child, _ = categories
    parent_product = create_product(parent, "parent-product")
    create_product(child, "child-product")

    response = api_client.get(
        reverse("products:product-list"),
        {"category": parent.slug},
    )

    assert [item["slug"] for item in response.json()["results"]] == [
        parent_product.slug
    ]


@pytest.mark.django_db
def test_product_list_filters_by_price_range(api_client, categories):
    category, _, _ = categories
    middle = create_product(category, "middle", price="20.00")
    create_product(category, "cheap", price="10.00")
    create_product(category, "expensive", price="30.00")

    response = api_client.get(
        reverse("products:product-list"),
        {"min_price": "15", "max_price": "25"},
    )

    assert [item["slug"] for item in response.json()["results"]] == [middle.slug]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("filter_value", "expected_slug"),
    [("true", "available"), ("false", "sold-out")],
)
def test_product_list_filters_by_stock(
    api_client,
    categories,
    filter_value,
    expected_slug,
):
    category, _, _ = categories
    create_product(category, "available", stock_quantity=2)
    create_product(category, "sold-out", stock_quantity=0)

    response = api_client.get(
        reverse("products:product-list"),
        {"in_stock": filter_value},
    )

    assert [item["slug"] for item in response.json()["results"]] == [expected_slug]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("search", "expected_slug"),
    [("ultrabook", "searchable-name"), ("ergonomic", "searchable-description")],
)
def test_product_list_searches_name_and_description(
    api_client,
    categories,
    search,
    expected_slug,
):
    category, _, _ = categories
    create_product(category, "searchable-name", name="Ultrabook Pro")
    create_product(
        category,
        "searchable-description",
        name="Office Laptop",
        description="Ergonomic business computer",
    )
    create_product(category, "unrelated", name="Desktop")

    response = api_client.get(
        reverse("products:product-list"),
        {"search": search},
    )

    assert [item["slug"] for item in response.json()["results"]] == [expected_slug]


@pytest.mark.django_db
def test_product_list_orders_by_price(api_client, categories):
    category, _, _ = categories
    create_product(category, "middle", price="20.00")
    create_product(category, "expensive", price="30.00")
    create_product(category, "cheap", price="10.00")

    response = api_client.get(
        reverse("products:product-list"),
        {"ordering": "price"},
    )

    assert [item["slug"] for item in response.json()["results"]] == [
        "cheap",
        "middle",
        "expensive",
    ]


@pytest.mark.django_db
def test_product_list_orders_by_creation_time(api_client, categories):
    category, _, _ = categories
    first = create_product(category, "first")
    second = create_product(category, "second")

    response = api_client.get(
        reverse("products:product-list"),
        {"ordering": "created_at"},
    )

    assert [item["id"] for item in response.json()["results"]] == [
        first.pk,
        second.pk,
    ]


@pytest.mark.django_db
def test_product_list_is_paginated(api_client, categories):
    category, _, _ = categories
    for index in range(3):
        create_product(
            category,
            f"product-{index}",
            price=f"{index + 1}.00",
        )

    response = api_client.get(
        reverse("products:product-list"),
        {"ordering": "price", "page_size": 2},
    )

    data = response.json()
    assert data["count"] == 3
    assert len(data["results"]) == 2
    assert data["next"] is not None
    assert data["previous"] is None


@pytest.mark.django_db
def test_invalid_product_filters_return_bad_request(api_client, categories):
    category, _, _ = categories
    create_product(category, "product")

    invalid_decimal = api_client.get(
        reverse("products:product-list"),
        {"min_price": "invalid"},
    )
    reversed_range = api_client.get(
        reverse("products:product-list"),
        {"min_price": "20", "max_price": "10"},
    )

    assert invalid_decimal.status_code == status.HTTP_400_BAD_REQUEST
    assert reversed_range.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query_params",
    [
        {"in_stock": "not-a-boolean"},
        {"max_price": "NaN"},
        {"min_price": "1.50"},
    ],
)
def test_malformed_product_filters_fail_safely(
    api_client,
    categories,
    query_params,
):
    category, _, _ = categories
    create_product(category, "product")

    response = api_client.get(reverse("products:product-list"), query_params)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_malformed_product_page_uses_standard_not_found_response(
    api_client,
    categories,
):
    category, _, _ = categories
    create_product(category, "product")

    response = api_client.get(
        reverse("products:product-list"),
        {"page": "not-a-page"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_public_catalog_endpoints_are_read_only(api_client, categories):
    category, _, _ = categories
    product = create_product(category, "product")

    for url in (
        reverse("products:category-list"),
        reverse("products:category-detail", kwargs={"slug": category.slug}),
        reverse("products:product-list"),
        reverse("products:product-detail", kwargs={"slug": product.slug}),
    ):
        assert (
            api_client.post(url, {}).status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        )


@pytest.mark.django_db
def test_product_list_avoids_category_and_image_n_plus_one_queries(
    api_client,
    categories,
    django_assert_num_queries,
):
    category, _, _ = categories
    first = create_product(category, "first")
    second = create_product(category, "second")
    create_image(first, 0)
    create_image(second, 0)

    with django_assert_num_queries(3):
        response = api_client.get(reverse("products:product-list"))

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_openapi_schema_documents_public_catalog_endpoints_and_filters(api_client):
    response = api_client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    expected_paths = {
        "/api/v1/categories/",
        "/api/v1/categories/{slug}/",
        "/api/v1/products/",
        "/api/v1/products/{slug}/",
    }
    assert expected_paths <= schema["paths"].keys()

    product_parameters = {
        parameter["name"]
        for parameter in schema["paths"]["/api/v1/products/"]["get"]["parameters"]
    }
    assert {
        "category",
        "min_price",
        "max_price",
        "in_stock",
        "search",
        "ordering",
        "page",
        "page_size",
    } <= product_parameters

    for path in expected_paths:
        assert schema["paths"][path]["get"]["security"] == [{}]

    schemas = schema["components"]["schemas"]
    assert set(schemas["ProductList"]["properties"]) == {
        "id",
        "name",
        "slug",
        "category",
        "price",
        "in_stock",
        "primary_image",
    }
    assert set(schemas["ProductDetail"]["properties"]) == {
        "id",
        "name",
        "slug",
        "category",
        "description",
        "price",
        "in_stock",
        "images",
    }
