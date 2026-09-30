from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.carts.models import Cart, CartItem
from apps.carts.services import (
    GuestCartNotFound,
    get_or_create_active_customer_cart,
    merge_guest_cart,
)
from apps.products.models import Category, Product


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    user = User.objects.create_user(
        "merge-customer@example.com",
        password="StrongPassword123!",
    )
    return CustomerProfile.objects.create(user=user)


@pytest.fixture
def category(db):
    return Category.objects.create(name="Merge products")


def create_product(category, slug, *, price="10.00", stock_quantity=10):
    return Product.objects.create(
        category=category,
        name=slug.replace("-", " ").title(),
        slug=slug,
        sku=slug.upper(),
        price=Decimal(price),
        stock_quantity=stock_quantity,
        status=Product.Status.ACTIVE,
    )


def merge(api_client, token=None):
    headers = {"HTTP_X_CART_TOKEN": str(token)} if token is not None else {}
    return api_client.post(reverse("carts:cart-merge"), **headers)


@pytest.mark.django_db
def test_merge_requires_authentication(api_client):
    guest_cart = Cart.objects.create()

    response = merge(api_client, guest_cart.token)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Cart.objects.filter(pk=guest_cart.pk, customer=None).exists()


@pytest.mark.django_db
def test_merge_requires_cart_token_header(api_client, customer):
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "X-Cart-Token header is required."}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "token",
    ["not-a-uuid", "00000000-0000-0000-0000-000000000000"],
)
def test_merge_rejects_malformed_or_unknown_token(api_client, customer, token):
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, token)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Guest cart not found."}


@pytest.mark.django_db
def test_customer_owned_token_is_rejected_like_unknown_token(api_client, customer):
    other_user = User.objects.create_user("other-merge@example.com")
    other_customer = CustomerProfile.objects.create(user=other_user)
    customer_cart = Cart.objects.create(customer=other_customer)
    api_client.force_authenticate(user=customer.user)

    owned_response = merge(api_client, customer_cart.token)
    unknown_response = merge(
        api_client,
        "00000000-0000-0000-0000-000000000000",
    )

    assert owned_response.status_code == status.HTTP_404_NOT_FOUND
    assert owned_response.json() == unknown_response.json()


@pytest.mark.django_db
def test_converted_guest_token_is_rejected(api_client, customer):
    guest_cart = Cart.objects.create(status=Cart.Status.CONVERTED)
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, guest_cart.token)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Guest cart not found."}


@pytest.mark.django_db
def test_guest_cart_is_claimed_when_customer_has_no_active_cart(
    api_client,
    customer,
    category,
):
    product = create_product(category, "claimed-product")
    guest_cart = Cart.objects.create()
    item = CartItem.objects.create(cart=guest_cart, product=product, quantity=3)
    original_created_at = item.created_at
    old_guest_token = guest_cart.token
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, guest_cart.token)

    assert response.status_code == status.HTTP_200_OK
    guest_cart.refresh_from_db()
    item.refresh_from_db()
    assert guest_cart.customer == customer
    assert guest_cart.token != old_guest_token
    assert item.cart == guest_cart
    assert item.quantity == 3
    assert item.created_at == original_created_at
    assert "X-Cart-Token" not in response

    api_client.force_authenticate(user=None)
    old_token_response = api_client.get(
        reverse("carts:cart-detail"),
        HTTP_X_CART_TOKEN=str(old_guest_token),
    )
    assert old_token_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_merge_transfers_disjoint_items_and_deletes_guest_cart(
    api_client,
    customer,
    category,
):
    customer_product = create_product(category, "customer-only")
    guest_product = create_product(category, "guest-only")
    customer_cart = Cart.objects.create(customer=customer)
    guest_cart = Cart.objects.create()
    customer_item = CartItem.objects.create(
        cart=customer_cart,
        product=customer_product,
        quantity=1,
    )
    guest_item = CartItem.objects.create(
        cart=guest_cart,
        product=guest_product,
        quantity=2,
    )
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, guest_cart.token)

    assert response.status_code == status.HTTP_200_OK
    guest_item.refresh_from_db()
    assert guest_item.cart == customer_cart
    assert Cart.objects.filter(pk=guest_cart.pk).exists() is False
    assert set(customer_cart.items.values_list("pk", flat=True)) == {
        customer_item.pk,
        guest_item.pk,
    }


@pytest.mark.django_db
def test_merge_adds_overlapping_quantities(api_client, customer, category):
    product = create_product(category, "overlap")
    customer_cart = Cart.objects.create(customer=customer)
    guest_cart = Cart.objects.create()
    customer_item = CartItem.objects.create(
        cart=customer_cart,
        product=product,
        quantity=2,
    )
    CartItem.objects.create(cart=guest_cart, product=product, quantity=3)
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, guest_cart.token)

    customer_item.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert customer_item.quantity == 5
    assert customer_cart.items.filter(product=product).count() == 1


@pytest.mark.django_db
def test_merge_preserves_combined_quantity_beyond_integer_range(
    customer,
    category,
):
    product = create_product(
        category,
        "large-overlap",
        stock_quantity=2_000_000_000,
    )
    customer_cart = Cart.objects.create(customer=customer)
    guest_cart = Cart.objects.create()
    customer_item = CartItem.objects.create(
        cart=customer_cart,
        product=product,
        quantity=1_500_000_000,
    )
    CartItem.objects.create(
        cart=guest_cart,
        product=product,
        quantity=1_500_000_000,
    )

    merge_guest_cart(customer=customer, guest_token=guest_cart.token)

    customer_item.refresh_from_db()
    assert customer_item.quantity == 3_000_000_000
    assert Cart.objects.filter(pk=guest_cart.pk).exists() is False


@pytest.mark.django_db
def test_merge_above_stock_preserves_quantity_and_reports_it(
    api_client,
    customer,
    category,
):
    product = create_product(category, "low-stock", stock_quantity=3)
    customer_cart = Cart.objects.create(customer=customer)
    guest_cart = Cart.objects.create()
    CartItem.objects.create(cart=customer_cart, product=product, quantity=2)
    CartItem.objects.create(cart=guest_cart, product=product, quantity=3)
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, guest_cart.token)

    item = response.json()["items"][0]
    assert item["quantity"] == 5
    assert item["is_available"] is False
    assert item["availability_reason"] == "insufficient_stock"


@pytest.mark.django_db
def test_merge_preserves_stale_guest_item(api_client, customer, category):
    product = create_product(category, "stale")
    guest_cart = Cart.objects.create()
    CartItem.objects.create(cart=guest_cart, product=product, quantity=2)
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=("status",))
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, guest_cart.token)

    item = response.json()["items"][0]
    assert item["quantity"] == 2
    assert item["is_available"] is False
    assert item["availability_reason"] == "unavailable"


@pytest.mark.django_db
def test_merge_uses_current_price_and_does_not_change_stock(
    api_client,
    customer,
    category,
):
    product = create_product(category, "current-price", price="8.00")
    guest_cart = Cart.objects.create()
    CartItem.objects.create(cart=guest_cart, product=product, quantity=2)
    product.price = Decimal("11.00")
    product.save(update_fields=("price",))
    api_client.force_authenticate(user=customer.user)

    response = merge(api_client, guest_cart.token)

    data = response.json()
    assert data["items"][0]["product"]["price"] == "11"
    assert data["items"][0]["line_total"] == "22"
    assert data["subtotal"] == "22"
    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_consumed_token_cannot_be_reused_or_double_quantities(
    api_client,
    customer,
    category,
):
    product = create_product(category, "retry")
    customer_cart = Cart.objects.create(customer=customer)
    guest_cart = Cart.objects.create()
    item = CartItem.objects.create(
        cart=customer_cart,
        product=product,
        quantity=2,
    )
    CartItem.objects.create(cart=guest_cart, product=product, quantity=3)
    token = guest_cart.token
    api_client.force_authenticate(user=customer.user)

    first_response = merge(api_client, token)
    second_response = merge(api_client, token)

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_404_NOT_FOUND
    item.refresh_from_db()
    assert item.quantity == 5
    assert customer.carts.filter(status=Cart.Status.ACTIVE).count() == 1


def _merge_in_thread(customer_id, token, barrier):
    close_old_connections()
    try:
        customer = CustomerProfile.objects.get(pk=customer_id)
        barrier.wait()
        try:
            merge_guest_cart(customer=customer, guest_token=token)
        except GuestCartNotFound:
            return "not-found"
        return "merged"
    finally:
        close_old_connections()


def _merge_returning_cart_id(customer_id, token, barrier):
    close_old_connections()
    try:
        customer = CustomerProfile.objects.get(pk=customer_id)
        barrier.wait()
        return merge_guest_cart(customer=customer, guest_token=token).pk
    finally:
        close_old_connections()


def _get_or_create_cart_in_thread(customer_id, barrier):
    close_old_connections()
    try:
        customer = CustomerProfile.objects.get(pk=customer_id)
        barrier.wait()
        cart, _ = get_or_create_active_customer_cart(customer=customer)
        return cart.pk
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_simultaneous_merge_consumes_guest_cart_only_once():
    user = User.objects.create_user("concurrent-merge@example.com")
    customer = CustomerProfile.objects.create(user=user)
    category = Category.objects.create(name="Concurrent merge")
    product = create_product(category, "concurrent-product", stock_quantity=20)
    customer_cart = Cart.objects.create(customer=customer)
    guest_cart = Cart.objects.create()
    item = CartItem.objects.create(
        cart=customer_cart,
        product=product,
        quantity=2,
    )
    CartItem.objects.create(cart=guest_cart, product=product, quantity=3)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _merge_in_thread,
                customer.pk,
                guest_cart.token,
                barrier,
            )
            for _ in range(2)
        ]
        results = [future.result(timeout=10) for future in futures]

    item.refresh_from_db()
    assert sorted(results) == ["merged", "not-found"]
    assert item.quantity == 5
    assert Cart.objects.filter(pk=guest_cart.pk).exists() is False
    assert customer.carts.filter(status=Cart.Status.ACTIVE).count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_merge_by_different_customers_has_one_winner():
    first_user = User.objects.create_user("first-concurrent-merge@example.com")
    second_user = User.objects.create_user("second-concurrent-merge@example.com")
    first_customer = CustomerProfile.objects.create(user=first_user)
    second_customer = CustomerProfile.objects.create(user=second_user)
    guest_cart = Cart.objects.create()
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _merge_in_thread,
                customer.pk,
                guest_cart.token,
                barrier,
            )
            for customer in (first_customer, second_customer)
        ]
        results = [future.result(timeout=10) for future in futures]

    guest_cart.refresh_from_db()
    assert sorted(results) == ["merged", "not-found"]
    assert guest_cart.customer_id in {first_customer.pk, second_customer.pk}
    assert Cart.objects.filter(status=Cart.Status.ACTIVE).count() == 1


@pytest.mark.django_db(transaction=True)
def test_merge_and_active_cart_creation_converge_on_one_cart():
    user = User.objects.create_user("merge-create-race@example.com")
    customer = CustomerProfile.objects.create(user=user)
    category = Category.objects.create(name="Merge create race")
    product = create_product(category, "merge-create-product")
    guest_cart = Cart.objects.create()
    item = CartItem.objects.create(cart=guest_cart, product=product, quantity=2)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        merge_future = executor.submit(
            _merge_returning_cart_id,
            customer.pk,
            guest_cart.token,
            barrier,
        )
        create_future = executor.submit(
            _get_or_create_cart_in_thread,
            customer.pk,
            barrier,
        )
        cart_ids = [
            merge_future.result(timeout=10),
            create_future.result(timeout=10),
        ]

    active_cart = Cart.objects.get(customer=customer, status=Cart.Status.ACTIVE)
    item.refresh_from_db()
    assert cart_ids == [active_cart.pk, active_cart.pk]
    assert item.cart == active_cart
    assert customer.carts.filter(status=Cart.Status.ACTIVE).count() == 1


@pytest.mark.django_db
def test_merge_endpoint_is_documented(api_client):
    response = api_client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    operation = response.json()["paths"]["/api/v1/cart/merge/"]["post"]
    token_parameter = next(
        parameter
        for parameter in operation["parameters"]
        if parameter["name"] == "X-Cart-Token"
    )
    assert token_parameter["in"] == "header"
    assert token_parameter["required"] is True
    assert operation["security"] == [{"jwtAuth": []}]
    assert "401" in operation["responses"]
