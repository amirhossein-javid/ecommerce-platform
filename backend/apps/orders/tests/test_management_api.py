from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import Order, OrderItem, Shipment
from apps.payments.models import PaymentAttempt
from apps.products.models import Category, Product


def create_operator(*permissions):
    operator = User.objects.create_user("dashboard-operator@example.com", "password")
    operator.is_staff = True
    operator.save(update_fields=("is_staff",))
    operator.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="orders", codename__in=permissions
        )
    )
    return operator


def create_order(*, status_value=Order.Status.PAID):
    user = User.objects.create_user(
        f"customer-{User.objects.count()}@example.com", "password"
    )
    customer = CustomerProfile.objects.create(
        user=user, first_name="سارا", last_name="اکبری"
    )
    order = Order.objects.create(
        customer=customer,
        status=status_value,
        subtotal=Decimal("1000"),
        discount_total=Decimal("0"),
        shipping_total=Decimal("0"),
        grand_total=Decimal("1000"),
        shipping_recipient_first_name="سارا",
        shipping_recipient_last_name="اکبری",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="اصفهان",
        shipping_city="اصفهان",
        shipping_address="میدان نقش جهان",
        shipping_postal_code="1234567890",
    )
    OrderItem.objects.create(
        order=order,
        product_name="گلدان",
        sku="VASE",
        unit_price=Decimal("500"),
        quantity=2,
        line_total=Decimal("1000"),
    )
    return order


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_staff_without_model_permission_cannot_access_order_management(api_client):
    api_client.force_authenticate(user=create_operator())

    response = api_client.get(reverse("orders:management-dashboard-summary"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_dashboard_metrics_are_backend_derived_and_do_not_double_count_revenue(
    api_client,
):
    paid = create_order()
    create_order(status_value=Order.Status.PROCESSING)
    PaymentAttempt.objects.create(
        order=paid, gateway="one", amount=paid.grand_total, status="SUCCESS"
    )
    PaymentAttempt.objects.create(
        order=paid, gateway="two", amount=paid.grand_total, status="SUCCESS"
    )
    category = Category.objects.create(name="میناکاری")
    Product.objects.create(
        category=category,
        name="کم‌موجود",
        sku="LOW",
        price=Decimal("100"),
        stock_quantity=5,
        status=Product.Status.ACTIVE,
    )
    Product.objects.create(
        category=category,
        name="پرموجود",
        sku="HIGH",
        price=Decimal("100"),
        stock_quantity=6,
        status=Product.Status.ACTIVE,
    )
    api_client.force_authenticate(user=create_operator("view_order"))

    response = api_client.get(reverse("orders:management-dashboard-summary"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "order_count": 2,
        "successful_revenue": "1000",
        "pending_fulfillment_count": 2,
        "low_stock_product_count": 1,
        "low_stock_threshold": 5,
    }


@pytest.mark.django_db
def test_order_management_lists_filters_and_returns_operational_detail(api_client):
    expected = create_order(status_value=Order.Status.PAID)
    create_order(status_value=Order.Status.DELIVERED)
    api_client.force_authenticate(user=create_operator("view_order"))

    listed = api_client.get(
        reverse("orders:management-order-list"),
        {"status": Order.Status.PAID, "search": str(expected.pk)},
    )
    detail = api_client.get(
        reverse("orders:management-order-detail", args=(expected.pk,))
    )

    assert listed.status_code == status.HTTP_200_OK
    assert [row["id"] for row in listed.json()["results"]] == [expected.pk]
    assert listed.json()["results"][0]["item_count"] == 2
    assert detail.status_code == status.HTTP_200_OK
    assert detail.json()["customer_display_name"] == "سارا اکبری"
    assert detail.json()["items"][0]["sku"] == "VASE"
    assert "payment_attempts" not in detail.json()


@pytest.mark.django_db
def test_order_transition_and_shipment_update_use_explicit_permissions(api_client):
    order = create_order(status_value=Order.Status.PAID)
    operator = create_operator("change_order", "change_shipment")
    api_client.force_authenticate(user=operator)

    processing = api_client.post(
        reverse("orders:management-order-transition", args=(order.pk,)),
        {"status": Order.Status.PROCESSING},
        format="json",
    )
    shipment = api_client.patch(
        reverse("orders:management-order-shipment", args=(order.pk,)),
        {"carrier": "  پست ایران  ", "tracking_number": "  TRACK-1  "},
        format="json",
    )
    shipped = api_client.post(
        reverse("orders:management-order-transition", args=(order.pk,)),
        {"status": Order.Status.SHIPPED},
        format="json",
    )

    assert processing.status_code == status.HTTP_200_OK
    assert shipment.status_code == status.HTTP_200_OK
    assert shipment.json()["shipment"]["carrier"] == "پست ایران"
    assert shipped.status_code == status.HTTP_200_OK
    assert shipped.json()["status"] == Order.Status.SHIPPED
    assert Shipment.objects.get(order=order).tracking_number == "TRACK-1"
    assert list(order.status_history.values_list("actor_user_id", flat=True)) == [
        operator.pk,
        operator.pk,
    ]


@pytest.mark.django_db
def test_shipment_permission_is_not_implied_by_order_change(api_client):
    order = create_order(status_value=Order.Status.PROCESSING)
    Shipment.objects.create(order=order)
    api_client.force_authenticate(user=create_operator("change_order"))

    response = api_client.patch(
        reverse("orders:management-order-shipment", args=(order.pk,)),
        {"carrier": "پست", "tracking_number": "TRACK"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
