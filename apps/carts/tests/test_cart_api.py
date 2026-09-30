from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.carts.models import Cart, CartItem
from apps.products.models import Category, Product, ProductImage


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category(db):
    return Category.objects.create(name="Cart API products")


@pytest.fixture
def product(category):
    return Product.objects.create(
        category=category,
        name="Shopping product",
        slug="shopping-product",
        sku="SHOPPING-PRODUCT",
        price=Decimal("12.00"),
        stock_quantity=10,
        status=Product.Status.ACTIVE,
    )


def create_customer(email):
    user = User.objects.create_user(email, password="StrongPassword123!")
    return CustomerProfile.objects.create(user=user)


def authenticate(api_client, customer):
    api_client.force_authenticate(user=customer.user)


def token_headers(cart):
    return {"HTTP_X_CART_TOKEN": str(cart.token)}


def add_item(api_client, product, quantity=1, **headers):
    return api_client.post(
        reverse("carts:cart-item-list"),
        {"product_slug": product.slug, "quantity": quantity},
        format="json",
        **headers,
    )


@pytest.mark.django_db
def test_guest_get_without_token_is_empty_and_creates_no_cart(api_client):
    response = api_client.get(reverse("carts:cart-detail"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"items": [], "subtotal": "0"}
    assert "X-Cart-Token" not in response
    assert Cart.objects.count() == 0


@pytest.mark.django_db
def test_cart_responses_are_not_cacheable_and_vary_by_credentials(api_client):
    cart = Cart.objects.create()

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(cart),
    )

    cache_control = response["Cache-Control"].lower()
    vary = {value.strip().lower() for value in response["Vary"].split(",")}
    assert "private" in cache_control
    assert "no-store" in cache_control
    assert {"authorization", "x-cart-token"} <= vary


@pytest.mark.django_db
def test_guest_first_add_creates_cart_and_returns_token(api_client, product):
    response = add_item(api_client, product, quantity=2)

    assert response.status_code == status.HTTP_200_OK
    cart = Cart.objects.get(customer=None)
    assert response["X-Cart-Token"] == str(cart.token)
    assert response.json()["items"][0]["quantity"] == 2


@pytest.mark.django_db
def test_guest_token_resolves_same_cart(api_client, product):
    add_response = add_item(api_client, product)
    token = add_response["X-Cart-Token"]

    second_add = add_item(
        api_client,
        product,
        quantity=2,
        HTTP_X_CART_TOKEN=token,
    )
    get_response = api_client.get(
        reverse("carts:cart-detail"),
        HTTP_X_CART_TOKEN=token,
    )

    assert Cart.objects.count() == 1
    assert second_add.json()["items"][0]["quantity"] == 3
    assert get_response.json()["items"][0]["quantity"] == 3


@pytest.mark.django_db
@pytest.mark.parametrize(
    "token", ["not-a-uuid", "00000000-0000-0000-0000-000000000000"]
)
def test_malformed_or_unknown_guest_token_returns_not_found(api_client, token):
    response = api_client.get(
        reverse("carts:cart-detail"),
        HTTP_X_CART_TOKEN=token,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cart not found."}


@pytest.mark.django_db
@pytest.mark.parametrize("cart_status", [Cart.Status.ACTIVE, Cart.Status.CONVERTED])
def test_guest_token_cannot_resolve_customer_or_converted_cart(
    api_client,
    cart_status,
):
    customer = create_customer(f"{cart_status.lower()}@example.com")
    cart = Cart.objects.create(customer=customer, status=cart_status)

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(cart),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cart not found."}


@pytest.mark.django_db
def test_customer_deletion_does_not_turn_owned_cart_into_guest_cart(
    api_client,
    product,
):
    customer = create_customer("deleted-cart-owner@example.com")
    cart = Cart.objects.create(customer=customer)
    CartItem.objects.create(cart=cart, product=product, quantity=1)
    token = cart.token

    customer.delete()
    response = api_client.get(
        reverse("carts:cart-detail"),
        HTTP_X_CART_TOKEN=str(token),
    )

    assert Cart.objects.filter(pk=cart.pk).exists() is False
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cart not found."}


@pytest.mark.django_db
def test_authenticated_customer_only_sees_own_cart(api_client, product):
    owner = create_customer("owner@example.com")
    other = create_customer("other@example.com")
    owner_cart = Cart.objects.create(customer=owner)
    other_cart = Cart.objects.create(customer=other)
    owner_item = CartItem.objects.create(
        cart=owner_cart,
        product=product,
        quantity=1,
    )
    other_item = CartItem.objects.create(
        cart=other_cart,
        product=product,
        quantity=2,
    )
    authenticate(api_client, owner)

    get_response = api_client.get(reverse("carts:cart-detail"))
    patch_response = api_client.patch(
        reverse("carts:cart-item-detail", kwargs={"pk": other_item.pk}),
        {"quantity": 3},
        format="json",
    )

    assert [item["id"] for item in get_response.json()["items"]] == [owner_item.pk]
    assert patch_response.status_code == status.HTTP_404_NOT_FOUND
    other_item.refresh_from_db()
    assert other_item.quantity == 2


@pytest.mark.django_db
def test_authenticated_request_ignores_guest_token(api_client, product):
    customer = create_customer("authenticated@example.com")
    guest_cart = Cart.objects.create()
    guest_item = CartItem.objects.create(
        cart=guest_cart,
        product=product,
        quantity=1,
    )
    authenticate(api_client, customer)

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(guest_cart),
    )
    delete_response = api_client.delete(
        reverse("carts:cart-item-detail", kwargs={"pk": guest_item.pk}),
        **token_headers(guest_cart),
    )

    assert response.json() == {"items": [], "subtotal": "0"}
    assert delete_response.status_code == status.HTTP_404_NOT_FOUND
    assert CartItem.objects.filter(pk=guest_item.pk).exists()


@pytest.mark.django_db
def test_authenticated_user_without_profile_cannot_fall_back_to_guest_token(
    api_client,
    product,
):
    system_user = User.objects.create_user("system@example.com")
    guest_cart = Cart.objects.create()
    guest_item = CartItem.objects.create(
        cart=guest_cart,
        product=product,
        quantity=1,
    )
    api_client.force_authenticate(user=system_user)

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(guest_cart),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Customer profile not found."}
    assert CartItem.objects.filter(pk=guest_item.pk).exists()


@pytest.mark.django_db
def test_authenticated_get_does_not_create_empty_cart(api_client):
    customer = create_customer("empty@example.com")
    authenticate(api_client, customer)

    response = api_client.get(reverse("carts:cart-detail"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"items": [], "subtotal": "0"}
    assert customer.carts.exists() is False


@pytest.mark.django_db
def test_authenticated_add_creates_customer_cart(api_client, product):
    customer = create_customer("add@example.com")
    authenticate(api_client, customer)

    response = add_item(api_client, product, quantity=2)

    cart = Cart.objects.get(customer=customer)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["quantity"] == 2
    assert "X-Cart-Token" not in response
    assert cart.items.get().product == product


@pytest.mark.django_db
def test_patch_updates_quantity(api_client, product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=1)

    response = api_client.patch(
        reverse("carts:cart-item-detail", kwargs={"pk": item.pk}),
        {"quantity": 4},
        format="json",
        **token_headers(cart),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["quantity"] == 4
    item.refresh_from_db()
    assert item.quantity == 4


@pytest.mark.django_db
def test_delete_removes_only_selected_item(api_client, category):
    first = Product.objects.create(
        category=category,
        name="First",
        slug="first",
        sku="FIRST",
        price=Decimal("1.00"),
        stock_quantity=5,
        status=Product.Status.ACTIVE,
    )
    second = Product.objects.create(
        category=category,
        name="Second",
        slug="second",
        sku="SECOND",
        price=Decimal("2.00"),
        stock_quantity=5,
        status=Product.Status.ACTIVE,
    )
    cart = Cart.objects.create()
    removed = CartItem.objects.create(cart=cart, product=first, quantity=1)
    retained = CartItem.objects.create(cart=cart, product=second, quantity=1)

    response = api_client.delete(
        reverse("carts:cart-item-detail", kwargs={"pk": removed.pk}),
        **token_headers(cart),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert CartItem.objects.filter(pk=removed.pk).exists() is False
    assert CartItem.objects.filter(pk=retained.pk).exists() is True


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [0, -1, "invalid"])
def test_add_rejects_invalid_quantity_without_creating_cart(
    api_client,
    product,
    quantity,
):
    response = add_item(api_client, product, quantity=quantity)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "quantity" in response.json()
    assert Cart.objects.exists() is False


@pytest.mark.django_db
def test_patch_does_not_treat_zero_as_deletion(api_client, product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=2)

    response = api_client.patch(
        reverse("carts:cart-item-detail", kwargs={"pk": item.pk}),
        {"quantity": 0},
        format="json",
        **token_headers(cart),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    item.refresh_from_db()
    assert item.quantity == 2


@pytest.mark.django_db
def test_quantity_above_stock_is_rejected_without_guest_cart(api_client, product):
    response = add_item(api_client, product, quantity=11)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "quantity" in response.json()
    assert Cart.objects.exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["product", "category"])
def test_unavailable_product_cannot_be_added(api_client, product, reason):
    if reason == "product":
        product.status = Product.Status.ARCHIVED
        product.save(update_fields=("status",))
    else:
        product.category.is_active = False
        product.category.save(update_fields=("is_active",))

    response = add_item(api_client, product)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"product_slug": ["Product is not currently available."]}
    assert Cart.objects.exists() is False


@pytest.mark.django_db
def test_stale_unavailable_item_remains_visible(api_client, product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=2)
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=("status",))

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(cart),
    )

    data = response.json()["items"][0]
    assert data["id"] == item.pk
    assert data["is_available"] is False
    assert data["availability_reason"] == "unavailable"
    assert CartItem.objects.filter(pk=item.pk, quantity=2).exists()


@pytest.mark.django_db
def test_stale_unavailable_item_cannot_be_incremented(api_client, product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=2)
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=("status",))

    response = add_item(
        api_client,
        product,
        HTTP_X_CART_TOKEN=str(cart.token),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    item.refresh_from_db()
    assert item.quantity == 2


@pytest.mark.django_db
def test_stock_decrease_reports_insufficient_stock_without_changing_item(
    api_client,
    product,
):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=5)
    product.stock_quantity = 2
    product.save(update_fields=("stock_quantity",))

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(cart),
    )

    data = response.json()["items"][0]
    assert data["is_available"] is False
    assert data["availability_reason"] == "insufficient_stock"
    assert data["quantity"] == 5
    item.refresh_from_db()
    assert item.quantity == 5


@pytest.mark.django_db
def test_cart_uses_current_prices_for_lines_and_subtotal(api_client, category):
    first = Product.objects.create(
        category=category,
        name="First price",
        slug="first-price",
        sku="FIRST-PRICE",
        price=Decimal("10.00"),
        stock_quantity=10,
        status=Product.Status.ACTIVE,
    )
    second = Product.objects.create(
        category=category,
        name="Second price",
        slug="second-price",
        sku="SECOND-PRICE",
        price=Decimal("3.00"),
        stock_quantity=10,
        status=Product.Status.ACTIVE,
    )
    cart = Cart.objects.create()
    CartItem.objects.create(cart=cart, product=first, quantity=2)
    CartItem.objects.create(cart=cart, product=second, quantity=3)
    first.price = Decimal("12.00")
    first.save(update_fields=("price",))

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(cart),
    )

    data = response.json()
    assert data["items"][0]["product"]["price"] == "12"
    assert data["items"][0]["line_total"] == "24"
    assert data["items"][1]["line_total"] == "9"
    assert data["subtotal"] == "33"


@pytest.mark.django_db
def test_cart_hides_sku_exact_stock_and_internal_cart_id(api_client, product):
    cart = Cart.objects.create()
    CartItem.objects.create(cart=cart, product=product, quantity=1)

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(cart),
    )

    data = response.json()
    assert set(data) == {"items", "subtotal"}
    assert set(data["items"][0]["product"]) == {
        "slug",
        "name",
        "price",
        "primary_image",
    }
    assert "sku" not in str(data).lower()
    assert "stock" not in str(data).lower()
    assert cart.pk not in data.values()


@pytest.mark.django_db
def test_cart_includes_primary_image(api_client, product):
    image = ProductImage.objects.create(
        product=product,
        image=f"products/{product.pk}/primary.jpg",
        alt_text="Primary view",
        position=0,
        is_primary=True,
    )
    cart = Cart.objects.create()
    CartItem.objects.create(cart=cart, product=product, quantity=1)

    response = api_client.get(
        reverse("carts:cart-detail"),
        **token_headers(cart),
    )

    assert response.json()["items"][0]["product"]["primary_image"] == {
        "id": image.pk,
        "image": f"http://testserver/media/{image.image.name}",
        "alt_text": "Primary view",
        "is_primary": True,
        "position": 0,
    }


@pytest.mark.django_db
def test_cart_mutations_do_not_change_stock(api_client, product):
    add_response = add_item(api_client, product, quantity=2)
    token = add_response["X-Cart-Token"]
    item_id = add_response.json()["items"][0]["id"]

    api_client.patch(
        reverse("carts:cart-item-detail", kwargs={"pk": item_id}),
        {"quantity": 4},
        format="json",
        HTTP_X_CART_TOKEN=token,
    )

    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_guest_cart_get_avoids_n_plus_one_queries(
    api_client,
    category,
    django_assert_num_queries,
):
    cart = Cart.objects.create()
    for index in range(3):
        product = Product.objects.create(
            category=category,
            name=f"Product {index}",
            slug=f"product-{index}",
            sku=f"PRODUCT-{index}",
            price=Decimal("2.00"),
            stock_quantity=5,
            status=Product.Status.ACTIVE,
        )
        CartItem.objects.create(cart=cart, product=product, quantity=1)

    with django_assert_num_queries(3):
        response = api_client.get(
            reverse("carts:cart-detail"),
            **token_headers(cart),
        )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["items"]) == 3


@pytest.mark.django_db
def test_cart_openapi_contract_and_schema_validation(api_client):
    response = api_client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert {
        "/api/v1/cart/",
        "/api/v1/cart/items/",
        "/api/v1/cart/items/{id}/",
    } <= schema["paths"].keys()
    assert "get" in schema["paths"]["/api/v1/cart/"]
    assert "post" in schema["paths"]["/api/v1/cart/items/"]
    assert {"patch", "delete"} <= schema["paths"]["/api/v1/cart/items/{id}/"].keys()

    get_parameters = schema["paths"]["/api/v1/cart/"]["get"]["parameters"]
    assert any(parameter["name"] == "X-Cart-Token" for parameter in get_parameters)
    post_response = schema["paths"]["/api/v1/cart/items/"]["post"]["responses"]["200"]
    assert "X-Cart-Token" in post_response["headers"]
