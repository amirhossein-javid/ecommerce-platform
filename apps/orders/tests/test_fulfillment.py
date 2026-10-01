from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.orders.admin import OrderAdmin, ShipmentAdmin
from apps.orders.lifecycle import (
    InvalidOrderTransition,
    InvalidOrderTransitionActor,
    ShipmentDetailsRequired,
    cancel_order,
    transition_order,
)
from apps.orders.models import Order, OrderStatusHistory, Shipment


def create_customer(email="fulfillment-customer@example.com"):
    user = User.objects.create_user(email, password="StrongPassword123!")
    return CustomerProfile.objects.create(user=user)


def create_operator(email="fulfillment-operator@example.com"):
    return User.objects.create_superuser(email, "StrongPassword123!")


def create_order(customer, *, status_value=Order.Status.PAID):
    return Order.objects.create(
        customer=customer,
        status=status_value,
        subtotal=Decimal("200"),
        discount_total=Decimal("0"),
        shipping_total=Decimal("0"),
        grand_total=Decimal("200"),
        shipping_title="Home",
        shipping_recipient_first_name="Fulfillment",
        shipping_recipient_last_name="Customer",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Fulfillment address",
        shipping_postal_code="1234567890",
    )


def transition_as_operator(order, operator, from_status, to_status, *, at=None):
    return transition_order(
        order=order,
        from_status=from_status,
        to_status=to_status,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
        at=at,
    )


def set_shipment_details(order, *, carrier="Post", tracking_number="TRACK-001"):
    shipment = order.shipment
    shipment.carrier = carrier
    shipment.tracking_number = tracking_number
    shipment.save()
    return shipment


@pytest.mark.django_db
def test_operator_runs_full_fulfillment_with_audit_and_exact_timestamps():
    customer = create_customer()
    operator = create_operator()
    order = create_order(customer)
    processing_at = timezone.now() - timedelta(minutes=3)
    shipped_at = timezone.now() - timedelta(minutes=2)
    delivered_at = timezone.now() - timedelta(minutes=1)

    processing = transition_as_operator(
        order,
        operator,
        Order.Status.PAID,
        Order.Status.PROCESSING,
        at=processing_at,
    )
    shipment = set_shipment_details(
        processing.order,
        carrier="  Iran Post  ",
        tracking_number="  TRACK-123  ",
    )
    shipped = transition_as_operator(
        processing.order,
        operator,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
        at=shipped_at,
    )
    delivered = transition_as_operator(
        shipped.order,
        operator,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
        at=delivered_at,
    )

    order.refresh_from_db()
    histories = list(order.status_history.order_by("created_at", "pk"))
    assert processing.changed is True
    assert shipped.changed is True
    assert delivered.changed is True
    assert order.status == Order.Status.DELIVERED
    assert order.processing_at == processing_at
    assert order.shipped_at == shipped_at
    assert order.delivered_at == delivered_at
    assert shipment.carrier == "Iran Post"
    assert shipment.tracking_number == "TRACK-123"
    assert [(row.from_status, row.to_status) for row in histories] == [
        (Order.Status.PAID, Order.Status.PROCESSING),
        (Order.Status.PROCESSING, Order.Status.SHIPPED),
        (Order.Status.SHIPPED, Order.Status.DELIVERED),
    ]
    assert all(
        row.actor_type == OrderStatusHistory.ActorType.OPERATOR
        and row.actor_user == operator
        for row in histories
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("source_status", "target_status"),
    [
        (Order.Status.PAID, Order.Status.SHIPPED),
        (Order.Status.PAID, Order.Status.DELIVERED),
        (Order.Status.PROCESSING, Order.Status.DELIVERED),
        (Order.Status.CANCELLED, Order.Status.PROCESSING),
        (Order.Status.EXPIRED, Order.Status.PROCESSING),
        (Order.Status.DELIVERED, Order.Status.PROCESSING),
    ],
)
def test_skipped_and_terminal_fulfillment_transitions_are_rejected(
    source_status,
    target_status,
):
    operator = create_operator()
    order = create_order(create_customer(), status_value=source_status)

    with pytest.raises(InvalidOrderTransition):
        transition_as_operator(order, operator, source_status, target_status)

    order.refresh_from_db()
    assert order.status == source_status
    assert order.status_history.exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("source_status", "target_status"),
    [
        (Order.Status.PAID, Order.Status.PROCESSING),
        (Order.Status.PROCESSING, Order.Status.SHIPPED),
        (Order.Status.SHIPPED, Order.Status.DELIVERED),
    ],
)
def test_customer_cannot_perform_fulfillment_transition(
    source_status,
    target_status,
):
    customer = create_customer()
    order = create_order(customer, status_value=source_status)

    with pytest.raises(InvalidOrderTransitionActor):
        transition_order(
            order=order,
            from_status=source_status,
            to_status=target_status,
            actor_type=OrderStatusHistory.ActorType.CUSTOMER,
            actor_user=customer.user,
        )

    assert order.status_history.exists() is False
    assert Shipment.objects.filter(order=order).exists() is False


@pytest.mark.django_db
def test_shipping_requires_complete_shipment_details():
    operator = create_operator()
    order = create_order(create_customer())
    transition_as_operator(
        order,
        operator,
        Order.Status.PAID,
        Order.Status.PROCESSING,
    )

    with pytest.raises(ShipmentDetailsRequired):
        transition_as_operator(
            order,
            operator,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
        )

    order.refresh_from_db()
    assert order.status == Order.Status.PROCESSING
    assert order.shipped_at is None
    assert order.status_history.count() == 1


@pytest.mark.django_db
def test_processing_creates_exactly_one_shipment_and_duplicate_is_idempotent():
    operator = create_operator()
    order = create_order(create_customer())
    processing_at = timezone.now()

    first = transition_as_operator(
        order,
        operator,
        Order.Status.PAID,
        Order.Status.PROCESSING,
        at=processing_at,
    )
    duplicate = transition_as_operator(
        order,
        operator,
        Order.Status.PAID,
        Order.Status.PROCESSING,
        at=processing_at + timedelta(minutes=1),
    )

    order.refresh_from_db()
    assert first.changed is True
    assert duplicate.changed is False
    assert order.processing_at == processing_at
    assert Shipment.objects.filter(order=order).count() == 1
    assert order.status_history.count() == 1


@pytest.mark.django_db
def test_duplicate_delivery_does_not_rewrite_timestamp_or_history():
    operator = create_operator()
    order = create_order(create_customer())
    transition_as_operator(
        order,
        operator,
        Order.Status.PAID,
        Order.Status.PROCESSING,
    )
    set_shipment_details(order)
    transition_as_operator(
        order,
        operator,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
    )
    delivered_at = timezone.now()
    transition_as_operator(
        order,
        operator,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
        at=delivered_at,
    )

    duplicate = transition_as_operator(
        order,
        operator,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
        at=delivered_at + timedelta(minutes=1),
    )

    order.refresh_from_db()
    assert duplicate.changed is False
    assert order.delivered_at == delivered_at
    assert order.status_history.count() == 3


@pytest.mark.django_db
def test_shipment_is_one_to_one_with_order():
    order = create_order(create_customer(), status_value=Order.Status.PROCESSING)
    Shipment.objects.create(order=order)

    with pytest.raises(IntegrityError), transaction.atomic():
        Shipment.objects.create(order=order)


@pytest.mark.django_db
def test_shipment_details_only_change_while_processing():
    operator = create_operator()
    order = create_order(create_customer())
    transition_as_operator(
        order,
        operator,
        Order.Status.PAID,
        Order.Status.PROCESSING,
    )
    shipment = order.shipment
    shipment.carrier = " "
    shipment.tracking_number = "TRACK-001"
    with pytest.raises(ValidationError):
        shipment.save()

    set_shipment_details(order)
    transition_as_operator(
        order,
        operator,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
    )
    shipment.refresh_from_db()
    shipment.carrier = "Changed carrier"
    with pytest.raises(ValidationError, match="only be changed"):
        shipment.save()

    shipment.refresh_from_db()
    assert shipment.carrier == "Post"
    assert shipment.tracking_number == "TRACK-001"


@pytest.mark.django_db
def test_shipped_order_cannot_be_cancelled():
    customer = create_customer()
    operator = create_operator()
    order = create_order(customer)
    transition_as_operator(
        order,
        operator,
        Order.Status.PAID,
        Order.Status.PROCESSING,
    )
    set_shipment_details(order)
    transition_as_operator(
        order,
        operator,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
    )

    with pytest.raises(InvalidOrderTransition):
        cancel_order(
            order=order,
            actor_type=OrderStatusHistory.ActorType.CUSTOMER,
            actor_user=customer.user,
        )

    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED


def test_order_and_shipment_use_restricted_custom_admins():
    order_admin = admin.site._registry[Order]
    shipment_admin = admin.site._registry[Shipment]

    assert isinstance(order_admin, OrderAdmin)
    assert isinstance(shipment_admin, ShipmentAdmin)
    assert "status" in order_admin.readonly_fields
    assert order_admin.actions == (
        "mark_processing",
        "mark_shipped",
        "mark_delivered",
    )


@pytest.mark.django_db
def test_admin_actions_and_shipment_edit_run_fulfillment_workflow(client):
    operator = create_operator()
    order = create_order(create_customer())
    client.force_login(operator)
    order_changelist = reverse("admin:orders_order_changelist")

    response = client.post(
        order_changelist,
        {
            "action": "mark_processing",
            "_selected_action": [str(order.pk)],
            "select_across": "0",
            "index": "0",
        },
    )
    order.refresh_from_db()
    assert response.status_code == 302
    assert order.status == Order.Status.PROCESSING
    shipment = order.shipment

    response = client.post(
        reverse("admin:orders_shipment_change", args=(shipment.pk,)),
        {
            "carrier": "Post",
            "tracking_number": "ADMIN-TRACK-001",
            "_save": "Save",
        },
    )
    shipment.refresh_from_db()
    assert response.status_code == 302
    assert shipment.carrier == "Post"
    assert shipment.tracking_number == "ADMIN-TRACK-001"

    for action, expected_status in (
        ("mark_shipped", Order.Status.SHIPPED),
        ("mark_delivered", Order.Status.DELIVERED),
    ):
        response = client.post(
            order_changelist,
            {
                "action": action,
                "_selected_action": [str(order.pk)],
                "select_across": "0",
                "index": "0",
            },
        )
        order.refresh_from_db()
        assert response.status_code == 302
        assert order.status == expected_status

    response = client.get(reverse("admin:orders_shipment_change", args=(shipment.pk,)))
    assert response.status_code == 200
    assert b'name="_save"' not in response.content
    assert order.status_history.count() == 3
