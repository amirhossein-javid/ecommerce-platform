from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.orders.lifecycle import (
    InvalidOrderTransition,
    InvalidOrderTransitionActor,
    RefundResolutionError,
    resolve_order_refund,
    transition_order,
)
from apps.orders.models import Order, OrderStatusHistory
from apps.payments.models import PaymentAttempt


def create_customer(email="lifecycle-customer@example.com"):
    user = User.objects.create_user(email)
    return CustomerProfile.objects.create(user=user)


def create_operator(email="operator@example.com"):
    return User.objects.create_superuser(email, "test-password")


def create_order(customer, *, status=Order.Status.PENDING_PAYMENT):
    return Order.objects.create(
        customer=customer,
        status=status,
        subtotal=Decimal("100.00"),
        discount_total=Decimal("10.00"),
        shipping_total=Decimal("5.00"),
        grand_total=Decimal("95.00"),
        shipping_title="Home",
        shipping_recipient_first_name="Lifecycle",
        shipping_recipient_last_name="Customer",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Lifecycle address",
        shipping_postal_code="1234567890",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (Order.Status.PAID, Order.Status.PROCESSING),
        (Order.Status.PAID, Order.Status.CANCELLED),
        (Order.Status.PROCESSING, Order.Status.SHIPPED),
        (Order.Status.PROCESSING, Order.Status.CANCELLED),
        (Order.Status.SHIPPED, Order.Status.DELIVERED),
    ],
)
def test_every_operator_transition_creates_one_history(from_status, to_status):
    operator = create_operator()
    order = create_order(create_customer(), status=from_status)

    result = transition_order(
        order=order,
        from_status=from_status,
        to_status=to_status,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
    )

    order.refresh_from_db()
    history = OrderStatusHistory.objects.get(order=order)
    assert result.changed is True
    assert order.status == to_status
    assert history.from_status == from_status
    assert history.to_status == to_status
    assert history.actor_type == OrderStatusHistory.ActorType.OPERATOR
    assert history.actor_user == operator


@pytest.mark.django_db
def test_customer_can_cancel_own_pending_order():
    customer = create_customer()
    order = create_order(customer)

    transition_order(
        order=order,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.CANCELLED,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
    )

    history = order.status_history.get()
    assert history.actor_user == customer.user
    assert history.actor_type == OrderStatusHistory.ActorType.CUSTOMER


@pytest.mark.django_db
@pytest.mark.parametrize("target", [Order.Status.PAID, Order.Status.EXPIRED])
@pytest.mark.parametrize(
    "actor_type",
    [OrderStatusHistory.ActorType.CUSTOMER, OrderStatusHistory.ActorType.OPERATOR],
)
def test_generic_callers_cannot_run_compound_system_transitions(target, actor_type):
    customer = create_customer()
    actor = customer.user if actor_type == "CUSTOMER" else create_operator()
    order = create_order(customer)

    with pytest.raises(InvalidOrderTransition, match="aggregate workflow"):
        transition_order(
            order=order,
            from_status=Order.Status.PENDING_PAYMENT,
            to_status=target,
            actor_type=actor_type,
            actor_user=actor,
        )

    order.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert OrderStatusHistory.objects.filter(order=order).exists() is False


@pytest.mark.django_db
def test_actor_action_mismatch_is_rejected_even_when_target_is_current_status():
    customer = create_customer()
    order = create_order(customer, status=Order.Status.PAID)

    with pytest.raises(InvalidOrderTransition, match="aggregate workflow"):
        transition_order(
            order=order,
            from_status=Order.Status.PENDING_PAYMENT,
            to_status=Order.Status.PAID,
            actor_type=OrderStatusHistory.ActorType.CUSTOMER,
            actor_user=customer.user,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (Order.Status.PENDING_PAYMENT, Order.Status.PROCESSING),
        (Order.Status.PAID, Order.Status.SHIPPED),
        (Order.Status.PROCESSING, Order.Status.DELIVERED),
        (Order.Status.SHIPPED, Order.Status.CANCELLED),
        (Order.Status.DELIVERED, Order.Status.CANCELLED),
        (Order.Status.CANCELLED, Order.Status.PROCESSING),
        (Order.Status.EXPIRED, Order.Status.CANCELLED),
    ],
)
def test_invalid_and_terminal_transitions_do_not_create_history(
    from_status,
    to_status,
):
    operator = create_operator()
    order = create_order(create_customer(), status=from_status)

    with pytest.raises(InvalidOrderTransition):
        transition_order(
            order=order,
            from_status=from_status,
            to_status=to_status,
            actor_type=OrderStatusHistory.ActorType.OPERATOR,
            actor_user=operator,
        )

    order.refresh_from_db()
    assert order.status == from_status
    assert OrderStatusHistory.objects.filter(order=order).exists() is False


@pytest.mark.django_db
def test_lifecycle_timestamps_and_same_command_idempotency():
    operator = create_operator()
    order = create_order(create_customer(), status=Order.Status.PAID)
    processing_at = timezone.now() - timedelta(minutes=3)
    shipped_at = timezone.now() - timedelta(minutes=2)
    delivered_at = timezone.now() - timedelta(minutes=1)

    transition_order(
        order=order,
        from_status=Order.Status.PAID,
        to_status=Order.Status.PROCESSING,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
        at=processing_at,
    )
    transition_order(
        order=order,
        from_status=Order.Status.PROCESSING,
        to_status=Order.Status.SHIPPED,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
        at=shipped_at,
    )
    transition_order(
        order=order,
        from_status=Order.Status.SHIPPED,
        to_status=Order.Status.DELIVERED,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
        at=delivered_at,
    )
    duplicate = transition_order(
        order=order,
        from_status=Order.Status.SHIPPED,
        to_status=Order.Status.DELIVERED,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
        at=timezone.now(),
    )

    order.refresh_from_db()
    assert duplicate.changed is False
    assert order.processing_at == processing_at
    assert order.shipped_at == shipped_at
    assert order.delivered_at == delivered_at
    assert OrderStatusHistory.objects.filter(order=order).count() == 3


@pytest.mark.django_db
def test_duplicate_from_different_actor_is_not_idempotent():
    first_operator = create_operator("first-operator@example.com")
    second_operator = create_operator("second-operator@example.com")
    order = create_order(create_customer(), status=Order.Status.PAID)
    transition_order(
        order=order,
        from_status=Order.Status.PAID,
        to_status=Order.Status.PROCESSING,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=first_operator,
    )

    with pytest.raises(InvalidOrderTransition, match="different command"):
        transition_order(
            order=order,
            from_status=Order.Status.PAID,
            to_status=Order.Status.PROCESSING,
            actor_type=OrderStatusHistory.ActorType.OPERATOR,
            actor_user=second_operator,
        )

    assert OrderStatusHistory.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_actor_identity_rules_are_enforced_without_history():
    customer = create_customer()
    other_customer = create_customer("other-lifecycle-customer@example.com")
    order = create_order(customer)

    with pytest.raises(InvalidOrderTransitionActor):
        transition_order(
            order=order,
            from_status=Order.Status.PENDING_PAYMENT,
            to_status=Order.Status.CANCELLED,
            actor_type=OrderStatusHistory.ActorType.CUSTOMER,
            actor_user=other_customer.user,
        )
    with pytest.raises(InvalidOrderTransitionActor):
        transition_order(
            order=order,
            from_status=Order.Status.PENDING_PAYMENT,
            to_status=Order.Status.CANCELLED,
            actor_type=OrderStatusHistory.ActorType.SYSTEM,
            actor_user=None,
        )

    assert OrderStatusHistory.objects.filter(order=order).exists() is False


@pytest.mark.django_db
def test_cancellation_refund_foundation_and_operator_resolution():
    customer = create_customer()
    operator = create_operator("refund-operator@example.com")
    unpaid = create_order(customer)
    paid = create_order(customer, status=Order.Status.PAID)
    cancelled_at = timezone.now() - timedelta(minutes=1)
    resolved_at = timezone.now()

    transition_order(
        order=unpaid,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.CANCELLED,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
    )
    transition_order(
        order=paid,
        from_status=Order.Status.PAID,
        to_status=Order.Status.CANCELLED,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
        at=cancelled_at,
    )
    resolution = resolve_order_refund(
        order=paid,
        operator=operator,
        at=resolved_at,
    )
    duplicate = resolve_order_refund(order=paid, operator=operator)

    unpaid.refresh_from_db()
    paid.refresh_from_db()
    assert unpaid.refund_status == Order.RefundStatus.NOT_REQUIRED
    assert paid.cancelled_at == cancelled_at
    assert paid.refund_status == Order.RefundStatus.RESOLVED
    assert paid.refund_resolved_at == resolved_at
    assert paid.refund_resolved_by == operator
    assert resolution.changed is True
    assert duplicate.changed is False


@pytest.mark.django_db
def test_refund_cannot_be_resolved_when_not_required():
    customer = create_customer()
    operator = create_operator("no-refund-operator@example.com")
    order = create_order(customer)
    transition_order(
        order=order,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.CANCELLED,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
    )

    with pytest.raises(RefundResolutionError):
        resolve_order_refund(order=order, operator=operator)


@pytest.mark.django_db
def test_paid_cancellation_requires_refund_without_rewriting_payment_success():
    customer = create_customer()
    operator = create_operator("payment-history-operator@example.com")
    order = create_order(customer, status=Order.Status.PAID)
    attempt = PaymentAttempt.objects.create(
        order=order,
        status=PaymentAttempt.Status.SUCCESS,
        amount=order.grand_total,
        gateway="test",
        gateway_reference="successful-payment",
    )

    transition_order(
        order=order,
        from_status=Order.Status.PAID,
        to_status=Order.Status.CANCELLED,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
    )

    order.refresh_from_db()
    attempt.refresh_from_db()
    assert order.refund_status == Order.RefundStatus.REQUIRED
    assert attempt.status == PaymentAttempt.Status.SUCCESS


@pytest.mark.django_db
def test_status_history_rejects_mutation_deletion_and_order_deletion():
    customer = create_customer()
    order = create_order(customer)
    transition_order(
        order=order,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.CANCELLED,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
    )
    history = order.status_history.get()

    history.to_status = Order.Status.EXPIRED
    with pytest.raises(TypeError, match="append-only"):
        history.save()
    with pytest.raises(TypeError, match="append-only"):
        history.delete()
    with pytest.raises(TypeError, match="append-only"):
        order.status_history.update(to_status=Order.Status.EXPIRED)
    with pytest.raises(TypeError, match="append-only"):
        order.status_history.all().delete()
    with pytest.raises(ProtectedError):
        order.delete()


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["from_status", "to_status"])
def test_database_rejects_unknown_history_status(field):
    order = create_order(create_customer())
    values = {
        "order": order,
        "from_status": Order.Status.PENDING_PAYMENT,
        "to_status": Order.Status.CANCELLED,
        "actor_type": OrderStatusHistory.ActorType.SYSTEM,
        field: "UNKNOWN",
    }

    with pytest.raises(IntegrityError), transaction.atomic():
        OrderStatusHistory.objects.create(**values)


def _cancel_in_thread(order_id, user_id, barrier):
    close_old_connections()
    try:
        order = Order.objects.get(pk=order_id)
        user = User.objects.get(pk=user_id)
        barrier.wait()
        result = transition_order(
            order=order,
            from_status=Order.Status.PENDING_PAYMENT,
            to_status=Order.Status.CANCELLED,
            actor_type=OrderStatusHistory.ActorType.CUSTOMER,
            actor_user=user,
        )
        return result.changed
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_transition_creates_exactly_one_history():
    customer = create_customer()
    order = create_order(customer)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _cancel_in_thread(order.pk, customer.user_id, barrier),
                range(2),
            )
        )

    order.refresh_from_db()
    assert sorted(results) == [False, True]
    assert order.status == Order.Status.CANCELLED
    assert OrderStatusHistory.objects.filter(order=order).count() == 1
