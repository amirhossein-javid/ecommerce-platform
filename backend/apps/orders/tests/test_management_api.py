from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.contrib.auth.models import Permission
from django.db import connection, connections
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import Order, OrderItem, OrderStatusHistory, Shipment
from apps.payments.models import PaymentAttempt
from apps.products.models import Category, Product


def create_operator(*permissions, email="dashboard-operator@example.com"):
    operator = User.objects.create_user(email, "password")
    operator.is_staff = True
    operator.save(update_fields=("is_staff",))
    operator.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="orders", codename__in=permissions
        )
    )
    return operator


def create_order(
    *,
    status_value=Order.Status.PAID,
    refund_status=Order.RefundStatus.NOT_REQUIRED,
):
    user = User.objects.create_user(
        f"customer-{User.objects.count()}@example.com", "password"
    )
    customer = CustomerProfile.objects.create(
        user=user, first_name="سارا", last_name="اکبری"
    )
    order = Order.objects.create(
        customer=customer,
        status=status_value,
        refund_status=refund_status,
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


@pytest.mark.django_db
def test_refund_resolution_requires_authentication_and_change_order_permission(
    api_client,
):
    order = create_order(
        status_value=Order.Status.CANCELLED,
        refund_status=Order.RefundStatus.REQUIRED,
    )
    url = reverse("orders:management-order-resolve-refund", args=(order.pk,))

    anonymous = api_client.post(url, format="json")

    customer = User.objects.create_user("refund-customer@example.com", "password")
    api_client.force_authenticate(user=customer)
    customer_response = api_client.post(url, format="json")

    api_client.force_authenticate(user=create_operator("view_order"))
    view_only = api_client.post(url, format="json")

    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert customer_response.status_code == status.HTTP_403_FORBIDDEN
    assert view_only.status_code == status.HTTP_403_FORBIDDEN
    order.refresh_from_db()
    assert order.refund_status == Order.RefundStatus.REQUIRED
    assert order.refund_resolved_at is None
    assert order.refund_resolved_by is None


@pytest.mark.django_db
def test_refund_resolution_is_idempotent_for_the_same_operator(api_client):
    order = create_order(
        status_value=Order.Status.CANCELLED,
        refund_status=Order.RefundStatus.REQUIRED,
    )
    operator = create_operator("change_order")
    api_client.force_authenticate(user=operator)
    url = reverse("orders:management-order-resolve-refund", args=(order.pk,))

    first = api_client.post(url, format="json")
    order.refresh_from_db()
    resolved_at = order.refund_resolved_at
    repeated = api_client.post(url, format="json")

    assert first.status_code == status.HTTP_200_OK
    assert repeated.status_code == status.HTTP_200_OK
    assert first.json()["refund_status"] == Order.RefundStatus.RESOLVED
    assert repeated.json()["refund_status"] == Order.RefundStatus.RESOLVED
    order.refresh_from_db()
    assert order.refund_resolved_at == resolved_at
    assert order.refund_resolved_by == operator


@pytest.mark.django_db
def test_refund_resolution_rejects_invalid_state_and_different_actor_replay(
    api_client,
):
    not_required = create_order(status_value=Order.Status.PAID)
    required = create_order(
        status_value=Order.Status.CANCELLED,
        refund_status=Order.RefundStatus.REQUIRED,
    )
    first_operator = create_operator("change_order")
    api_client.force_authenticate(user=first_operator)
    resolved = api_client.post(
        reverse("orders:management-order-resolve-refund", args=(required.pk,)),
        format="json",
    )

    second_operator = User.objects.create_user(
        "second-refund-operator@example.com", "password"
    )
    second_operator.is_staff = True
    second_operator.save(update_fields=("is_staff",))
    second_operator.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="orders", codename="change_order"
        )
    )
    api_client.force_authenticate(user=second_operator)
    invalid_state = api_client.post(
        reverse("orders:management-order-resolve-refund", args=(not_required.pk,)),
        format="json",
    )
    different_actor = api_client.post(
        reverse("orders:management-order-resolve-refund", args=(required.pk,)),
        format="json",
    )

    assert resolved.status_code == status.HTTP_200_OK
    assert invalid_state.status_code == status.HTTP_409_CONFLICT
    assert invalid_state.json() == {"detail": "The order does not require a refund."}
    assert different_actor.status_code == status.HTTP_409_CONFLICT
    assert different_actor.json() == {
        "detail": "The refund was resolved through a different command."
    }


@pytest.mark.django_db
def test_refund_resolution_returns_not_found_for_unknown_order(api_client):
    api_client.force_authenticate(user=create_operator("change_order"))

    response = api_client.post(
        reverse("orders:management-order-resolve-refund", args=(999_999,)),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Order not found."}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("source", "target"),
    (
        (Order.Status.PAID, Order.Status.PROCESSING),
        (Order.Status.PROCESSING, Order.Status.SHIPPED),
        (Order.Status.SHIPPED, Order.Status.DELIVERED),
    ),
)
def test_management_transition_replay_preserves_history_and_side_effects(
    api_client, source, target
):
    order = create_order(status_value=source)
    if source != Order.Status.PAID:
        Shipment.objects.create(order=order, carrier="Post", tracking_number="TRACK")
    operator = create_operator("change_order")
    api_client.force_authenticate(user=operator)
    url = reverse("orders:management-order-transition", args=(order.pk,))

    first = api_client.post(url, {"status": target}, format="json")
    shipment = Shipment.objects.get(order=order)
    shipment_snapshot = (shipment.pk, shipment.created_at, shipment.updated_at)
    repeated = api_client.post(url, {"status": target}, format="json")

    assert first.status_code == status.HTTP_200_OK
    assert repeated.status_code == status.HTTP_200_OK
    assert repeated.json() == first.json()
    history = order.status_history.get()
    assert (history.from_status, history.to_status) == (source, target)
    assert history.actor_type == OrderStatusHistory.ActorType.OPERATOR
    assert history.actor_user_id == operator.pk
    shipment.refresh_from_db()
    assert Shipment.objects.filter(order=order).count() == 1
    assert (shipment.pk, shipment.created_at, shipment.updated_at) == shipment_snapshot


@pytest.mark.django_db
def test_management_transition_replay_rejects_different_actor(api_client):
    order = create_order()
    first_operator = create_operator("change_order")
    second_operator = create_operator("change_order", email="second@example.com")
    url = reverse("orders:management-order-transition", args=(order.pk,))
    api_client.force_authenticate(user=first_operator)
    assert (
        api_client.post(
            url, {"status": Order.Status.PROCESSING}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )

    api_client.force_authenticate(user=second_operator)
    repeated = api_client.post(url, {"status": Order.Status.PROCESSING}, format="json")

    assert repeated.status_code == status.HTTP_409_CONFLICT
    assert order.status_history.get().actor_user_id == first_operator.pk


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("source", "target"),
    (
        (Order.Status.PROCESSING, Order.Status.PROCESSING),
        (Order.Status.PENDING_PAYMENT, Order.Status.PROCESSING),
        (Order.Status.PAID, Order.Status.SHIPPED),
        (Order.Status.DELIVERED, Order.Status.PROCESSING),
    ),
)
def test_management_transition_without_valid_transition_or_replay_is_rejected(
    api_client, source, target
):
    order = create_order(status_value=source)
    api_client.force_authenticate(user=create_operator("change_order"))

    response = api_client.post(
        reverse("orders:management-order-transition", args=(order.pk,)),
        {"status": target},
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    order.refresh_from_db()
    assert order.status == source
    assert not order.status_history.exists()
    assert not Shipment.objects.filter(order=order).exists()


@pytest.mark.django_db
def test_management_transition_rejects_changed_action_and_stale_retry(api_client):
    order = create_order()
    api_client.force_authenticate(user=create_operator("change_order"))
    url = reverse("orders:management-order-transition", args=(order.pk,))
    assert (
        api_client.post(
            url, {"status": Order.Status.PROCESSING}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )

    # A different action must run its own validation, never replay PROCESSING.
    invalid_shipping = api_client.post(
        url, {"status": Order.Status.SHIPPED}, format="json"
    )
    assert invalid_shipping.status_code == status.HTTP_409_CONFLICT
    assert order.status_history.count() == 1
    shipment = Shipment.objects.get(order=order)
    shipment.carrier = "Post"
    shipment.tracking_number = "TRACK"
    shipment.save()
    assert (
        api_client.post(
            url, {"status": Order.Status.SHIPPED}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )
    order.refresh_from_db()
    updated_at = order.updated_at

    stale = api_client.post(url, {"status": Order.Status.PROCESSING}, format="json")

    assert stale.status_code == status.HTTP_409_CONFLICT
    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED
    assert order.updated_at == updated_at
    assert order.status_history.count() == 2


@pytest.mark.django_db
def test_management_transition_replay_requires_current_permission(api_client):
    order = create_order()
    operator = create_operator("change_order")
    api_client.force_authenticate(user=operator)
    url = reverse("orders:management-order-transition", args=(order.pk,))
    assert (
        api_client.post(
            url, {"status": Order.Status.PROCESSING}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )
    operator.user_permissions.clear()
    api_client.force_authenticate(user=User.objects.get(pk=operator.pk))

    repeated = api_client.post(url, {"status": Order.Status.PROCESSING}, format="json")

    assert repeated.status_code == status.HTTP_403_FORBIDDEN
    assert order.status_history.count() == 1


@pytest.mark.django_db
def test_management_replay_rejects_history_inconsistent_with_locked_order(api_client):
    order = create_order()
    operator = create_operator("change_order")
    api_client.force_authenticate(user=operator)
    url = reverse("orders:management-order-transition", args=(order.pk,))
    assert (
        api_client.post(
            url, {"status": Order.Status.PROCESSING}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )
    # An older match is insufficient if the latest persisted event disagrees.
    OrderStatusHistory.objects.create(
        order=order,
        from_status=Order.Status.PROCESSING,
        to_status=Order.Status.SHIPPED,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
    )

    response = api_client.post(url, {"status": Order.Status.PROCESSING}, format="json")

    assert response.status_code == status.HTTP_409_CONFLICT
    order.refresh_from_db()
    assert order.status == Order.Status.PROCESSING
    assert order.status_history.count() == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_actor", (True, False))
def test_concurrent_management_transitions_preserve_actor_specific_replay(same_actor):
    order = create_order()
    first = create_operator("change_order")
    second = (
        first
        if same_actor
        else create_operator("change_order", email="second@example.com")
    )
    barrier = Barrier(2)

    def post_transition(user_id):
        try:
            client = APIClient()
            client.force_authenticate(user=User.objects.get(pk=user_id))
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pid = cursor.fetchone()[0]
            barrier.wait(timeout=10)
            response = client.post(
                reverse("orders:management-order-transition", args=(order.pk,)),
                {"status": Order.Status.PROCESSING},
                format="json",
            )
            return response.status_code, user_id, pid
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(post_transition, user.pk) for user in (first, second)
        ]
        results = [future.result(timeout=15) for future in futures]

    assert len({pid for _, _, pid in results}) == 2
    expected_codes = [200, 200] if same_actor else [200, 409]
    assert sorted(code for code, _, _ in results) == expected_codes
    order.refresh_from_db()
    assert order.status == Order.Status.PROCESSING
    history = order.status_history.get()
    assert history.actor_user_id in {
        user_id for code, user_id, _ in results if code == 200
    }
    assert order.processing_at == history.created_at
    assert Shipment.objects.filter(order=order).count() == 1
