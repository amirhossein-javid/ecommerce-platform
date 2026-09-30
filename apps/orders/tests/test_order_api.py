from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Address, CustomerProfile, User
from apps.orders.models import InventoryReservation, Order, OrderItem
from apps.products.models import Category, Product


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    return create_customer("orders-customer@example.com")


def create_customer(email):
    user = User.objects.create_user(email, password="StrongPassword123!")
    return CustomerProfile.objects.create(user=user)


def create_order(customer, *, status_value=Order.Status.PENDING_PAYMENT):
    return Order.objects.create(
        customer=customer,
        status=status_value,
        subtotal=Decimal("25.00"),
        discount_total=Decimal("0.00"),
        shipping_total=Decimal("0.00"),
        grand_total=Decimal("25.00"),
        shipping_title="Home",
        shipping_recipient_first_name="علی",
        shipping_recipient_last_name="احمدی",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="تهران",
        shipping_city="تهران",
        shipping_address="نشانی تاریخی",
        shipping_postal_code="1234567890",
    )


def create_order_item(order, *, product=None):
    return OrderItem.objects.create(
        order=order,
        product=product,
        product_name="Historical Product",
        sku="HISTORICAL-SKU",
        unit_price=Decimal("12.00"),
        quantity=2,
        line_total=Decimal("24.00"),
    )


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", ["orders:order-list", "orders:order-detail"])
def test_customer_order_apis_require_authentication(api_client, customer, url_name):
    order = create_order(customer)
    kwargs = {"pk": order.pk} if url_name.endswith("detail") else None

    response = api_client.get(reverse(url_name, kwargs=kwargs))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_order_list_is_owned_paginated_and_newest_first(api_client, customer):
    other_customer = create_customer("other-orders@example.com")
    own_orders = [create_order(customer) for _ in range(3)]
    create_order(other_customer)
    api_client.force_authenticate(user=customer.user)

    response = api_client.get(reverse("orders:order-list"), {"page_size": 2})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["count"] == 3
    assert [row["id"] for row in response.json()["results"]] == [
        own_orders[2].pk,
        own_orders[1].pk,
    ]
    assert response.json()["next"] is not None


@pytest.mark.django_db
def test_order_detail_returns_snapshots_without_inventory_data(
    api_client,
    customer,
):
    category = Category.objects.create(name="Historical category")
    product = Product.objects.create(
        category=category,
        name="Current Product",
        slug="historical-product",
        sku="CURRENT-SKU",
        price=Decimal("99.00"),
        stock_quantity=10,
        status=Product.Status.ACTIVE,
    )
    address = Address.objects.create(
        customer_profile=customer,
        title="Current address",
        recipient_first_name="رضا",
        recipient_last_name="کاظمی",
        recipient_phone_number="+989121234568",
        province="البرز",
        city="کرج",
        address="نشانی فعلی",
        postal_code="1234567891",
        is_default=True,
    )
    order = create_order(customer)
    create_order_item(order, product=product)
    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=2,
        expires_at=order.created_at.replace(year=order.created_at.year + 1),
    )
    product.name = "Changed Product"
    product.sku = "CHANGED-SKU"
    product.price = Decimal("1.00")
    product.save()
    address.delete()
    api_client.force_authenticate(user=customer.user)

    response = api_client.get(reverse("orders:order-detail", kwargs={"pk": order.pk}))

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shipping_title"] == "Home"
    assert data["shipping_city"] == "تهران"
    assert data["shipping_address"] == "نشانی تاریخی"
    assert data["items"] == [
        {
            "product_name": "Historical Product",
            "sku": "HISTORICAL-SKU",
            "unit_price": "12",
            "quantity": 2,
            "line_total": "24",
        }
    ]
    assert "inventory_reservations" not in data
    assert "payment_expires_at" not in data
    assert "product" not in data["items"][0]


@pytest.mark.django_db
def test_cross_customer_and_unknown_order_have_identical_response(
    api_client,
    customer,
):
    other_customer = create_customer("isolated-orders@example.com")
    other_order = create_order(other_customer)
    api_client.force_authenticate(user=customer.user)

    cross_customer = api_client.get(
        reverse("orders:order-detail", kwargs={"pk": other_order.pk})
    )
    unknown = api_client.get(
        reverse("orders:order-detail", kwargs={"pk": other_order.pk + 99999})
    )

    assert cross_customer.status_code == status.HTTP_404_NOT_FOUND
    assert cross_customer.json() == unknown.json()


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", ["orders:order-list", "orders:order-detail"])
def test_authenticated_user_without_profile_receives_safe_not_found(
    api_client,
    url_name,
):
    user = User.objects.create_user(
        "staff-without-customer@example.com",
        password="StrongPassword123!",
    )
    api_client.force_authenticate(user=user)
    kwargs = {"pk": 1} if url_name.endswith("detail") else None

    response = api_client.get(reverse(url_name, kwargs=kwargs))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Customer profile not found."}


@pytest.mark.django_db
def test_customer_order_endpoints_are_read_only(api_client, customer):
    order = create_order(customer)
    api_client.force_authenticate(user=customer.user)

    list_response = api_client.post(reverse("orders:order-list"), {})
    detail_response = api_client.patch(
        reverse("orders:order-detail", kwargs={"pk": order.pk}),
        {"status": Order.Status.CANCELLED},
    )

    assert list_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert detail_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    order.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT


@pytest.mark.django_db
def test_order_list_query_count_is_constant(
    api_client,
    customer,
    django_assert_num_queries,
):
    for _ in range(5):
        create_order(customer)
    api_client.force_authenticate(user=customer.user)

    with django_assert_num_queries(3):
        response = api_client.get(reverse("orders:order-list"))

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["results"]) == 5


@pytest.mark.django_db
def test_order_detail_prefetches_items_in_constant_queries(
    api_client,
    customer,
    django_assert_num_queries,
):
    order = create_order(customer)
    for _ in range(5):
        create_order_item(order)
    api_client.force_authenticate(user=customer.user)

    with django_assert_num_queries(3):
        response = api_client.get(
            reverse("orders:order-detail", kwargs={"pk": order.pk})
        )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["items"]) == 5


@pytest.mark.django_db
def test_customer_order_endpoints_are_documented(api_client):
    response = api_client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    paths = response.json()["paths"]
    for path in ("/api/v1/orders/", "/api/v1/orders/{id}/"):
        operation = paths[path]["get"]
        assert operation["security"] == [{"jwtAuth": []}]
        assert {"200", "401", "404"} <= operation["responses"].keys()
