from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import (
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from apps.payments.models import PaymentAttempt
from apps.products.models import Category, Product


def create_order(*, status=Order.Status.PENDING_PAYMENT, refund_status=None):
    customer = CustomerProfile.objects.create(
        user=User.objects.create_user(f"customer-{status}@example.com")
    )
    values = {
        "customer": customer,
        "status": status,
        "subtotal": Decimal("100"),
        "grand_total": Decimal("100"),
        "shipping_recipient_first_name": "Customer",
        "shipping_recipient_last_name": "Name",
        "shipping_recipient_phone_number": "+989121234567",
        "shipping_province": "Tehran",
        "shipping_city": "Tehran",
        "shipping_address": "Address",
        "shipping_postal_code": "1234567890",
    }
    if refund_status is not None:
        values["refund_status"] = refund_status
    return Order.objects.create(**values)


def post_action(client, action, order):
    return client.post(
        reverse("admin:orders_order_changelist"),
        {
            "action": action,
            "_selected_action": [str(order.pk)],
            "select_across": "0",
            "index": "0",
        },
    )


@pytest.mark.django_db
def test_order_admin_direct_post_cannot_mutate_lifecycle_state(client):
    operator = User.objects.create_superuser("admin@example.com", "password")
    order = create_order()
    client.force_login(operator)

    response = client.post(
        reverse("admin:orders_order_change", args=(order.pk,)),
        {
            "status": Order.Status.PAID,
            "refund_status": Order.RefundStatus.RESOLVED,
            "paid_at": timezone.now(),
            "items-TOTAL_FORMS": "0",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "inventory_reservations-TOTAL_FORMS": "0",
            "inventory_reservations-INITIAL_FORMS": "0",
            "inventory_reservations-MIN_NUM_FORMS": "0",
            "inventory_reservations-MAX_NUM_FORMS": "1000",
            "status_history-TOTAL_FORMS": "0",
            "status_history-INITIAL_FORMS": "0",
            "status_history-MIN_NUM_FORMS": "0",
            "status_history-MAX_NUM_FORMS": "1000",
            "_save": "Save",
        },
    )

    assert response.status_code == 403
    order.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert order.refund_status == Order.RefundStatus.NOT_REQUIRED
    assert order.paid_at is None
    assert order.status_history.exists() is False


@pytest.mark.django_db
def test_view_only_staff_cannot_invoke_order_actions(client):
    viewer = User.objects.create_user("viewer@example.com", "password")
    viewer.is_staff = True
    viewer.save(update_fields=("is_staff",))
    viewer.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="orders",
            codename="view_order",
        )
    )
    order = create_order()
    client.force_login(viewer)

    response = post_action(client, "cancel_orders", order)

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert order.status_history.exists() is False


@pytest.mark.django_db
def test_admin_cancellation_action_uses_compound_domain_workflow(client):
    operator = User.objects.create_superuser("admin@example.com", "password")
    order = create_order()
    category = Category.objects.create(name="Category")
    product = Product.objects.create(
        category=category,
        name="Product",
        sku="ADMIN-CANCEL",
        price=Decimal("100"),
        stock_quantity=5,
    )
    reservation = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    attempt = PaymentAttempt.objects.create(
        order=order,
        amount=order.grand_total,
        gateway="test",
    )
    client.force_login(operator)

    response = post_action(client, "cancel_orders", order)

    assert response.status_code == 302
    order.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.cancelled_at is not None
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert attempt.status == PaymentAttempt.Status.FAILED
    history = OrderStatusHistory.objects.get(order=order)
    assert history.actor_type == OrderStatusHistory.ActorType.OPERATOR
    assert history.actor_user == operator


@pytest.mark.django_db
def test_admin_paid_cancellation_restores_stock_exactly_once(client):
    operator = User.objects.create_superuser("admin@example.com", "password")
    order = create_order(status=Order.Status.PAID)
    category = Category.objects.create(name="Category")
    product = Product.objects.create(
        category=category,
        name="Product",
        sku="ADMIN-PAID-CANCEL",
        price=Decimal("100"),
        stock_quantity=4,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        sku=product.sku,
        unit_price=product.price,
        quantity=1,
        line_total=product.price,
    )
    reservation = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        status=InventoryReservation.Status.CONSUMED,
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    attempt = PaymentAttempt.objects.create(
        order=order,
        amount=order.grand_total,
        gateway="test",
        status=PaymentAttempt.Status.SUCCESS,
    )
    client.force_login(operator)

    first_response = post_action(client, "cancel_orders", order)
    second_response = post_action(client, "cancel_orders", order)

    assert first_response.status_code == 302
    assert second_response.status_code == 302
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.refund_status == Order.RefundStatus.REQUIRED
    assert product.stock_quantity == 5
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert order.status_history.count() == 1


@pytest.mark.django_db
def test_admin_refund_resolution_action_uses_domain_service(client):
    operator = User.objects.create_superuser("admin@example.com", "password")
    order = create_order(
        status=Order.Status.CANCELLED,
        refund_status=Order.RefundStatus.REQUIRED,
    )
    client.force_login(operator)

    response = post_action(client, "resolve_refunds", order)

    assert response.status_code == 302
    order.refresh_from_db()
    assert order.refund_status == Order.RefundStatus.RESOLVED
    assert order.refund_resolved_by == operator
    assert order.refund_resolved_at is not None
