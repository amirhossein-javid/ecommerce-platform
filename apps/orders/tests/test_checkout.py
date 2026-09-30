from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Address, CustomerProfile, User
from apps.carts.models import Cart, CartItem
from apps.orders.models import InventoryReservation, Order, OrderItem
from apps.orders.services import (
    RESERVATION_LIFETIME,
    CheckoutCartUnavailable,
    CheckoutInsufficientStock,
    InsufficientAvailableStock,
    checkout_customer_cart,
)
from apps.products.models import Category, Product


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    return create_customer("checkout-customer@example.com")


@pytest.fixture
def default_address(customer):
    return create_address(customer, title="Default", is_default=True)


@pytest.fixture
def category(db):
    return Category.objects.create(name="Checkout products")


@pytest.fixture
def product(category):
    return create_product(category, "checkout-product", price="12.50")


def create_customer(email):
    user = User.objects.create_user(email, password="StrongPassword123!")
    return CustomerProfile.objects.create(user=user)


def create_address(customer, *, title, is_default=False, city="تهران"):
    return Address.objects.create(
        customer_profile=customer,
        title=title,
        recipient_first_name="علی",
        recipient_last_name="احمدی",
        recipient_phone_number="+989121234567",
        province="تهران",
        city=city,
        address=f"نشانی {title}",
        postal_code="1234567890",
        is_default=is_default,
    )


def create_product(
    category,
    slug,
    *,
    price="10.00",
    stock_quantity=10,
    product_status=Product.Status.ACTIVE,
):
    return Product.objects.create(
        category=category,
        name=slug.replace("-", " ").title(),
        slug=slug,
        sku=slug.upper(),
        price=Decimal(price),
        stock_quantity=stock_quantity,
        status=product_status,
    )


def create_cart(customer, lines):
    cart = Cart.objects.create(customer=customer)
    for product, quantity in lines:
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
        )
    return cart


def create_zero_order(customer):
    return Order.objects.create(
        customer=customer,
        subtotal=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        shipping_total=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        shipping_title="Previous",
        shipping_recipient_first_name="علی",
        shipping_recipient_last_name="احمدی",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="تهران",
        shipping_city="تهران",
        shipping_address="نشانی قبلی",
        shipping_postal_code="1234567890",
    )


def checkout(api_client, data=None):
    return api_client.post(
        reverse("orders:checkout"),
        data or {},
        format="json",
    )


@pytest.mark.django_db
def test_checkout_requires_authentication(api_client):
    response = checkout(api_client)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_checkout_uses_default_address_and_returns_pending_order(
    api_client,
    customer,
    default_address,
    product,
):
    cart = create_cart(customer, [(product, 2)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    order = Order.objects.get(pk=data["id"])
    reservation = order.inventory_reservations.get()
    cart.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert data["shipping_title"] == default_address.title
    assert data["shipping_city"] == default_address.city
    assert data["status"] == Order.Status.PENDING_PAYMENT
    assert parse_datetime(data["payment_expires_at"]) == reservation.expires_at
    assert cart.status == Cart.Status.CONVERTED
    assert "inventory_reservations" not in data
    assert "stock_quantity" not in str(data)


@pytest.mark.django_db
def test_checkout_uses_explicit_owned_address(
    api_client,
    customer,
    default_address,
    product,
):
    explicit = create_address(customer, title="Work", city="کرج")
    create_cart(customer, [(product, 1)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client, {"address_id": explicit.pk})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["shipping_title"] == "Work"
    assert response.json()["shipping_city"] == "کرج"


@pytest.mark.django_db
def test_checkout_rejects_cross_customer_address_without_leaking_ownership(
    api_client,
    customer,
    default_address,
    product,
):
    other = create_customer("other-checkout@example.com")
    other_address = create_address(other, title="Other", is_default=True)
    create_cart(customer, [(product, 1)])
    api_client.force_authenticate(user=customer.user)

    cross_customer = checkout(api_client, {"address_id": other_address.pk})
    unknown = checkout(api_client, {"address_id": 999999})

    assert cross_customer.status_code == status.HTTP_400_BAD_REQUEST
    assert cross_customer.json() == unknown.json()
    assert Order.objects.exists() is False


@pytest.mark.django_db
def test_checkout_fails_without_usable_address(api_client, customer, product):
    create_cart(customer, [(product, 1)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": ["A usable shipping address is required."]}
    assert Order.objects.exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize("cart_state", ["missing", "empty"])
def test_checkout_rejects_missing_or_empty_cart(
    api_client,
    customer,
    default_address,
    cart_state,
):
    if cart_state == "empty":
        Cart.objects.create(customer=customer)
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": ["An active, non-empty cart is required."]}
    assert Order.objects.exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize("unavailable_reason", ["product", "category"])
def test_checkout_rejects_stale_unavailable_cart_item(
    api_client,
    customer,
    default_address,
    product,
    unavailable_reason,
):
    cart = create_cart(customer, [(product, 1)])
    if unavailable_reason == "product":
        product.status = Product.Status.ARCHIVED
        product.save(update_fields=("status",))
    else:
        product.category.is_active = False
        product.category.save(update_fields=("is_active",))
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": ["The cart contains an unavailable product."]}
    cart.refresh_from_db()
    assert cart.status == Cart.Status.ACTIVE
    assert Order.objects.exists() is False


@pytest.mark.django_db
def test_checkout_preserves_direct_category_visibility_semantics(
    api_client,
    customer,
    default_address,
    category,
):
    parent = Category.objects.create(name="Inactive ancestor", is_active=False)
    category.parent = parent
    category.save(update_fields=("parent",))
    product = create_product(category, "visible-child-product")
    create_cart(customer, [(product, 1)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_checkout_rejects_quantity_above_available_stock(
    api_client,
    customer,
    default_address,
    product,
):
    product.stock_quantity = 2
    product.save(update_fields=("stock_quantity",))
    cart = create_cart(customer, [(product, 3)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    cart.refresh_from_db()
    assert cart.status == Cart.Status.ACTIVE
    assert Order.objects.exists() is False
    assert InventoryReservation.objects.exists() is False


@pytest.mark.django_db
def test_checkout_counts_active_nonexpired_reservations(
    api_client,
    customer,
    default_address,
    product,
):
    product.stock_quantity = 5
    product.save(update_fields=("stock_quantity",))
    previous_order = create_zero_order(customer)
    InventoryReservation.objects.create(
        order=previous_order,
        product=product,
        quantity=3,
        expires_at=timezone.now() + RESERVATION_LIFETIME,
    )
    create_cart(customer, [(product, 3)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.count() == 1


@pytest.mark.django_db
def test_checkout_ignores_expired_active_reservations(
    api_client,
    customer,
    default_address,
    product,
):
    product.stock_quantity = 3
    product.save(update_fields=("stock_quantity",))
    previous_order = create_zero_order(customer)
    expired = InventoryReservation.objects.create(
        order=previous_order,
        product=product,
        quantity=3,
        expires_at=timezone.now() + RESERVATION_LIFETIME,
    )
    now = timezone.now()
    InventoryReservation.objects.filter(pk=expired.pk).update(
        created_at=now - RESERVATION_LIFETIME,
        expires_at=now,
    )
    create_cart(customer, [(product, 3)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_201_CREATED
    assert Order.objects.count() == 2


@pytest.mark.django_db
def test_checkout_uses_current_prices_and_server_calculated_totals(
    api_client,
    customer,
    default_address,
    category,
):
    first = create_product(category, "first-price", price="10.00")
    second = create_product(category, "second-price", price="3.50")
    cart = create_cart(customer, [(first, 2), (second, 3)])
    first.price = Decimal("12.00")
    first.save(update_fields=("price",))
    api_client.force_authenticate(user=customer.user)

    response = checkout(
        api_client,
        {
            "subtotal": "0.01",
            "discount_total": "999.00",
            "shipping_total": "999.00",
            "grand_total": "0.01",
        },
    )

    data = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    assert data["subtotal"] == "34.50"
    assert data["discount_total"] == "0.00"
    assert data["shipping_total"] == "0.00"
    assert data["grand_total"] == "34.50"
    assert [item["line_total"] for item in data["items"]] == ["24.00", "10.50"]
    cart.refresh_from_db()
    assert cart.status == Cart.Status.CONVERTED


@pytest.mark.django_db
def test_checkout_supports_totals_from_valid_product_price_and_stock_ranges(
    api_client,
    customer,
    default_address,
    category,
):
    product = create_product(
        category,
        "large-valid-total",
        price="9999999999.99",
        stock_quantity=10000,
    )
    create_cart(customer, [(product, 10000)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["subtotal"] == "99999999999900.00"
    assert response.json()["items"][0]["line_total"] == "99999999999900.00"


@pytest.mark.django_db
def test_checkout_preserves_product_and_address_snapshots(
    api_client,
    customer,
    default_address,
    product,
):
    create_cart(customer, [(product, 2)])
    api_client.force_authenticate(user=customer.user)
    response = checkout(api_client)
    order = Order.objects.get(pk=response.json()["id"])
    item = order.items.get()

    product.name = "Changed"
    product.sku = "CHANGED"
    product.price = Decimal("99.00")
    product.save()
    default_address.city = "کرج"
    default_address.address = "نشانی جدید"
    default_address.save()
    order.refresh_from_db()
    item.refresh_from_db()

    assert item.product_name == "Checkout Product"
    assert item.sku == "CHECKOUT-PRODUCT"
    assert item.unit_price == Decimal("12.50")
    assert order.shipping_city == "تهران"
    assert order.shipping_address == "نشانی Default"


@pytest.mark.django_db
def test_checkout_does_not_mutate_stock(
    api_client,
    customer,
    default_address,
    product,
):
    create_cart(customer, [(product, 4)])
    api_client.force_authenticate(user=customer.user)

    response = checkout(api_client)

    assert response.status_code == status.HTTP_201_CREATED
    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_repeated_checkout_does_not_create_duplicate_order(
    api_client,
    customer,
    default_address,
    product,
):
    create_cart(customer, [(product, 1)])
    api_client.force_authenticate(user=customer.user)

    first = checkout(api_client)
    second = checkout(api_client)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.count() == 1
    assert InventoryReservation.objects.count() == 1


@pytest.mark.django_db
def test_reservation_failure_rolls_back_order_items_and_cart(
    monkeypatch,
    customer,
    default_address,
    product,
):
    cart = create_cart(customer, [(product, 1)])

    def fail_reservation_creation(**kwargs):
        raise InsufficientAvailableStock(product.pk)

    monkeypatch.setattr(
        "apps.orders.services._create_reservations_for_locked_products",
        fail_reservation_creation,
    )

    with pytest.raises(InsufficientAvailableStock):
        checkout_customer_cart(customer=customer)

    cart.refresh_from_db()
    assert cart.status == Cart.Status.ACTIVE
    assert Order.objects.exists() is False
    assert OrderItem.objects.exists() is False
    assert InventoryReservation.objects.exists() is False


def _checkout_in_thread(customer_id, barrier):
    close_old_connections()
    try:
        customer = CustomerProfile.objects.get(pk=customer_id)
        barrier.wait()
        try:
            order = checkout_customer_cart(customer=customer)
        except CheckoutCartUnavailable:
            return "cart-unavailable"
        except (CheckoutInsufficientStock, InsufficientAvailableStock):
            return "insufficient"
        return f"created:{order.pk}"
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkout_of_same_cart_creates_one_order():
    customer = create_customer("same-cart-race@example.com")
    create_address(customer, title="Default", is_default=True)
    category = Category.objects.create(name="Same cart race")
    product = create_product(category, "same-cart-product")
    cart = create_cart(customer, [(product, 1)])
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_checkout_in_thread, customer.pk, barrier) for _ in range(2)
        ]
        results = [future.result(timeout=10) for future in futures]

    cart.refresh_from_db()
    assert sum(result.startswith("created:") for result in results) == 1
    assert "cart-unavailable" in results
    assert Order.objects.count() == 1
    assert cart.status == Cart.Status.CONVERTED


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkouts_cannot_oversell_shared_product():
    first_customer = create_customer("first-stock-race@example.com")
    second_customer = create_customer("second-stock-race@example.com")
    create_address(first_customer, title="First", is_default=True)
    create_address(second_customer, title="Second", is_default=True)
    category = Category.objects.create(name="Checkout stock race")
    product = create_product(category, "stock-race-product", stock_quantity=5)
    first_cart = create_cart(first_customer, [(product, 4)])
    second_cart = create_cart(second_customer, [(product, 4)])
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            _checkout_in_thread,
            first_customer.pk,
            barrier,
        )
        second_future = executor.submit(
            _checkout_in_thread,
            second_customer.pk,
            barrier,
        )
        results = [
            first_future.result(timeout=10),
            second_future.result(timeout=10),
        ]

    first_cart.refresh_from_db()
    second_cart.refresh_from_db()
    assert sum(result.startswith("created:") for result in results) == 1
    assert "insufficient" in results
    assert Order.objects.count() == 1
    assert {first_cart.status, second_cart.status} == {
        Cart.Status.ACTIVE,
        Cart.Status.CONVERTED,
    }
    active_reserved = InventoryReservation.objects.filter(
        product=product,
        status=InventoryReservation.Status.ACTIVE,
        expires_at__gt=timezone.now(),
    ).aggregate(total=Sum("quantity", default=0))["total"]
    assert active_reserved == 4
    product.refresh_from_db()
    assert product.stock_quantity == 5


@pytest.mark.django_db
def test_checkout_is_documented_in_openapi(api_client):
    response = api_client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    operation = response.json()["paths"]["/api/v1/checkout/"]["post"]
    assert operation["security"] == [{"jwtAuth": []}]
    assert {"201", "400", "401", "404"} <= operation["responses"].keys()
