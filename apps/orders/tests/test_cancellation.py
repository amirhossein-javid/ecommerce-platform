import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.common.money import STORE_CURRENCY
from apps.orders.lifecycle import (
    InvalidOrderTransition,
    InvalidOrderTransitionActor,
    cancel_order,
    resolve_order_refund,
)
from apps.orders.models import (
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from apps.payments.gateways import PaymentVerification, VerificationStatus
from apps.payments.models import PaymentAttempt
from apps.payments.services import finalize_verified_payment
from apps.products.models import Category, Product


def create_customer(email="cancellation-customer@example.com"):
    user = User.objects.create_user(email, password="StrongPassword123!")
    return CustomerProfile.objects.create(user=user)


def create_operator(email="cancellation-operator@example.com"):
    return User.objects.create_superuser(email, "StrongPassword123!")


def create_product(*, stock_quantity=10):
    category = Category.objects.create(name="Cancellation category")
    return Product.objects.create(
        category=category,
        name="Cancellation product",
        sku=f"CANCEL-{category.pk}",
        price=Decimal("100"),
        stock_quantity=stock_quantity,
        status=Product.Status.ACTIVE,
    )


def create_order(customer, *, status_value=Order.Status.PENDING_PAYMENT):
    return Order.objects.create(
        customer=customer,
        status=status_value,
        subtotal=Decimal("200"),
        discount_total=Decimal("0"),
        shipping_total=Decimal("0"),
        grand_total=Decimal("200"),
        shipping_title="Home",
        shipping_recipient_first_name="Cancellation",
        shipping_recipient_last_name="Customer",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Cancellation address",
        shipping_postal_code="1234567890",
    )


def add_inventory(order, product, *, item_quantity=2, reservation_status):
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        sku=product.sku,
        unit_price=product.price,
        quantity=item_quantity,
        line_total=product.price * item_quantity,
    )
    return InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        status=reservation_status,
        expires_at=timezone.now() + timedelta(minutes=15),
    )


def create_attempt(order, *, attempt_status):
    return PaymentAttempt.objects.create(
        order=order,
        status=attempt_status,
        amount=order.grand_total,
        currency=STORE_CURRENCY,
        gateway="test",
        gateway_reference=f"cancel-attempt-{order.pk}",
    )


@pytest.mark.django_db(transaction=True)
def test_paid_cancellation_logs_committed_restoration_context_once(caplog):
    customer = create_customer()
    operator = create_operator()
    product = create_product(stock_quantity=8)
    order = create_order(customer, status_value=Order.Status.PAID)
    add_inventory(
        order,
        product,
        item_quantity=2,
        reservation_status=InventoryReservation.Status.CONSUMED,
    )
    create_attempt(order, attempt_status=PaymentAttempt.Status.SUCCESS)
    caplog.set_level(logging.INFO, logger="apps.orders.lifecycle")

    first = cancel_order(
        order=order,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
    )
    duplicate = cancel_order(
        order=order,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
    )

    assert first.changed is True
    assert duplicate.changed is False
    effect_logs = [
        record.getMessage()
        for record in caplog.records
        if "order_cancellation_effects_committed" in record.getMessage()
    ]
    assert len(effect_logs) == 1
    message = effect_logs[0]
    assert f"order_id={order.pk}" in message
    assert "previous_status=PAID" in message
    assert "refund_status=REQUIRED" in message
    assert "restored_product_count=1" in message
    assert "restored_quantity=2" in message
    assert "actor_type=OPERATOR" in message
    assert f"actor_user_id={operator.pk}" in message

    resolve_order_refund(order=order, operator=operator)
    refund_logs = [
        record.getMessage()
        for record in caplog.records
        if "order_refund_resolved" in record.getMessage()
    ]
    assert len(refund_logs) == 1
    assert f"order_id={order.pk}" in refund_logs[0]
    assert f"operator_id={operator.pk}" in refund_logs[0]
    assert "refund_status=RESOLVED" in refund_logs[0]


@pytest.mark.django_db
def test_pending_cancellation_releases_reservation_without_changing_stock():
    customer = create_customer()
    product = create_product(stock_quantity=10)
    order = create_order(customer)
    reservation = add_inventory(
        order,
        product,
        reservation_status=InventoryReservation.Status.ACTIVE,
    )
    attempt = create_attempt(order, attempt_status=PaymentAttempt.Status.PENDING)

    result = cancel_order(
        order=order,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
    )

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    history = OrderStatusHistory.objects.get(order=order)
    assert result.changed is True
    assert order.status == Order.Status.CANCELLED
    assert order.refund_status == Order.RefundStatus.NOT_REQUIRED
    assert order.cancelled_at is not None
    assert product.stock_quantity == 10
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert attempt.status == PaymentAttempt.Status.FAILED
    assert history.from_status == Order.Status.PENDING_PAYMENT
    assert history.to_status == Order.Status.CANCELLED
    assert history.actor_type == OrderStatusHistory.ActorType.CUSTOMER
    assert history.actor_user == customer.user


@pytest.mark.django_db
@pytest.mark.parametrize("source_status", [Order.Status.PAID, Order.Status.PROCESSING])
def test_paid_cancellation_restores_item_stock_and_preserves_consumed_payment(
    source_status,
):
    customer = create_customer()
    operator = create_operator()
    product = create_product(stock_quantity=8)
    order = create_order(customer, status_value=source_status)
    reservation = add_inventory(
        order,
        product,
        item_quantity=2,
        reservation_status=InventoryReservation.Status.CONSUMED,
    )
    attempt = create_attempt(order, attempt_status=PaymentAttempt.Status.SUCCESS)

    cancel_order(
        order=order,
        actor_type=OrderStatusHistory.ActorType.OPERATOR,
        actor_user=operator,
    )

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    history = OrderStatusHistory.objects.get(order=order)
    assert order.status == Order.Status.CANCELLED
    assert order.refund_status == Order.RefundStatus.REQUIRED
    assert product.stock_quantity == 10
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert history.from_status == source_status
    assert history.actor_type == OrderStatusHistory.ActorType.OPERATOR
    assert history.actor_user == operator


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source_status",
    [Order.Status.SHIPPED, Order.Status.DELIVERED, Order.Status.EXPIRED],
)
def test_terminal_or_fulfilled_order_cannot_be_cancelled(source_status):
    customer = create_customer()
    order = create_order(customer, status_value=source_status)

    with pytest.raises(InvalidOrderTransition):
        cancel_order(
            order=order,
            actor_type=OrderStatusHistory.ActorType.CUSTOMER,
            actor_user=customer.user,
        )

    order.refresh_from_db()
    assert order.status == source_status
    assert OrderStatusHistory.objects.filter(order=order).exists() is False


@pytest.mark.django_db
def test_duplicate_paid_cancellation_has_no_repeated_side_effects():
    customer = create_customer()
    product = create_product(stock_quantity=8)
    order = create_order(customer, status_value=Order.Status.PAID)
    add_inventory(
        order,
        product,
        reservation_status=InventoryReservation.Status.CONSUMED,
    )
    attempt = create_attempt(order, attempt_status=PaymentAttempt.Status.SUCCESS)

    first = cancel_order(
        order=order,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
    )
    first_cancelled_at = first.order.cancelled_at
    duplicate = cancel_order(
        order=order,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
        at=timezone.now() + timedelta(minutes=1),
    )

    order.refresh_from_db()
    product.refresh_from_db()
    attempt.refresh_from_db()
    assert first.changed is True
    assert duplicate.changed is False
    assert product.stock_quantity == 10
    assert order.cancelled_at == first_cancelled_at
    assert order.refund_status == Order.RefundStatus.REQUIRED
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert OrderStatusHistory.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_different_actor_cannot_claim_cancel_idempotency():
    customer = create_customer()
    operator = create_operator()
    order = create_order(customer)
    cancel_order(
        order=order,
        actor_type=OrderStatusHistory.ActorType.CUSTOMER,
        actor_user=customer.user,
    )

    with pytest.raises(InvalidOrderTransition, match="different command"):
        cancel_order(
            order=order,
            actor_type=OrderStatusHistory.ActorType.OPERATOR,
            actor_user=operator,
        )

    assert OrderStatusHistory.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_customer_cannot_cancel_another_customers_order():
    customer = create_customer()
    other = create_customer("other-cancellation-customer@example.com")
    order = create_order(customer)

    with pytest.raises(InvalidOrderTransitionActor):
        cancel_order(
            order=order,
            actor_type=OrderStatusHistory.ActorType.CUSTOMER,
            actor_user=other.user,
        )


@pytest.mark.django_db
def test_cancel_api_is_owned_authenticated_and_idempotent():
    customer = create_customer()
    order = create_order(customer)
    client = APIClient()
    url = reverse("orders:order-cancel", kwargs={"pk": order.pk})

    assert client.post(url).status_code == status.HTTP_401_UNAUTHORIZED
    client.force_authenticate(customer.user)
    first = client.post(url)
    duplicate = client.post(url)

    assert first.status_code == status.HTTP_200_OK
    assert first.json()["status"] == Order.Status.CANCELLED
    assert first.json()["refund_status"] == Order.RefundStatus.NOT_REQUIRED
    assert first.json()["cancelled_at"] is not None
    assert duplicate.status_code == status.HTTP_200_OK
    assert OrderStatusHistory.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_cancel_api_hides_cross_customer_order_and_user_without_profile():
    owner = create_customer()
    other = create_customer("cancel-api-other@example.com")
    order = create_order(owner)
    client = APIClient()
    url = reverse("orders:order-cancel", kwargs={"pk": order.pk})

    client.force_authenticate(other.user)
    cross_customer = client.post(url)
    unknown = client.post(reverse("orders:order-cancel", kwargs={"pk": order.pk + 1}))
    user_without_profile = User.objects.create_user("cancel-no-profile@example.com")
    client.force_authenticate(user_without_profile)
    no_profile = client.post(url)

    assert cross_customer.status_code == status.HTTP_404_NOT_FOUND
    assert cross_customer.json() == unknown.json()
    assert no_profile.status_code == status.HTTP_404_NOT_FOUND
    assert no_profile.json() == {"detail": "Customer profile not found."}


@pytest.mark.django_db
def test_cancel_api_rejects_non_cancellable_status():
    customer = create_customer()
    order = create_order(customer, status_value=Order.Status.SHIPPED)
    client = APIClient()
    client.force_authenticate(customer.user)

    response = client.post(reverse("orders:order-cancel", kwargs={"pk": order.pk}))

    assert response.status_code == status.HTTP_409_CONFLICT
    assert order.status_history.exists() is False


@pytest.mark.django_db
def test_cancel_api_is_in_openapi_schema():
    response = APIClient().get(reverse("schema"), {"format": "json"})

    operation = response.json()["paths"]["/api/v1/orders/{id}/cancel/"]["post"]
    assert operation["security"] == [{"jwtAuth": []}]
    assert {"200", "401", "404", "409"} <= operation["responses"].keys()


def _cancel_in_thread(order_id, user_id, barrier):
    close_old_connections()
    try:
        order = Order.objects.get(pk=order_id)
        user = User.objects.get(pk=user_id)
        barrier.wait()
        try:
            result = cancel_order(
                order=order,
                actor_type=OrderStatusHistory.ActorType.CUSTOMER,
                actor_user=user,
            )
        except InvalidOrderTransition:
            return "rejected"
        return "changed" if result.changed else "duplicate"
    finally:
        close_old_connections()


def _finalize_in_thread(attempt_id, barrier, *, at=None):
    close_old_connections()
    try:
        attempt = PaymentAttempt.objects.get(pk=attempt_id)
        verification = PaymentVerification(
            status=VerificationStatus.SUCCESS,
            gateway_reference=attempt.gateway_reference,
            amount=attempt.amount,
            currency=attempt.currency,
        )
        barrier.wait()
        result = finalize_verified_payment(
            attempt=attempt,
            verification=verification,
            at=at,
        )
        return result.status
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_paid_cancellation_restores_stock_once():
    customer = create_customer()
    product = create_product(stock_quantity=8)
    order = create_order(customer, status_value=Order.Status.PAID)
    add_inventory(
        order,
        product,
        reservation_status=InventoryReservation.Status.CONSUMED,
    )
    create_attempt(order, attempt_status=PaymentAttempt.Status.SUCCESS)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _cancel_in_thread(order.pk, customer.user_id, barrier),
                range(2),
            )
        )

    order.refresh_from_db()
    product.refresh_from_db()
    assert sorted(results) == ["changed", "duplicate"]
    assert order.status == Order.Status.CANCELLED
    assert product.stock_quantity == 10
    assert OrderStatusHistory.objects.filter(order=order).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_cancellation_and_payment_success_preserve_inventory_once():
    customer = create_customer()
    product = create_product(stock_quantity=10)
    order = create_order(customer)
    reservation = add_inventory(
        order,
        product,
        reservation_status=InventoryReservation.Status.ACTIVE,
    )
    attempt = create_attempt(order, attempt_status=PaymentAttempt.Status.PENDING)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        cancel_future = executor.submit(
            _cancel_in_thread,
            order.pk,
            customer.user_id,
            barrier,
        )
        payment_future = executor.submit(
            _finalize_in_thread,
            attempt.pk,
            barrier,
        )
        assert cancel_future.result() == "changed"
        payment_result = payment_future.result()

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert product.stock_quantity == 10
    assert (
        OrderStatusHistory.objects.filter(
            order=order,
            to_status=Order.Status.CANCELLED,
        ).count()
        == 1
    )
    if payment_result == PaymentAttempt.Status.SUCCESS:
        assert attempt.status == PaymentAttempt.Status.SUCCESS
        assert reservation.status == InventoryReservation.Status.CONSUMED
        assert order.refund_status == Order.RefundStatus.REQUIRED
        assert (
            OrderStatusHistory.objects.filter(
                order=order,
                to_status=Order.Status.PAID,
            ).count()
            == 1
        )
    else:
        assert payment_result == PaymentAttempt.Status.FAILED
        assert attempt.status == PaymentAttempt.Status.FAILED
        assert reservation.status == InventoryReservation.Status.RELEASED
        assert order.refund_status == Order.RefundStatus.NOT_REQUIRED
        assert (
            OrderStatusHistory.objects.filter(
                order=order,
                to_status=Order.Status.PAID,
            ).exists()
            is False
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_cancellation_and_expiry_commit_only_lock_winner():
    customer = create_customer()
    product = create_product(stock_quantity=10)
    order = create_order(customer)
    reservation = add_inventory(
        order,
        product,
        reservation_status=InventoryReservation.Status.ACTIVE,
    )
    attempt = create_attempt(order, attempt_status=PaymentAttempt.Status.PENDING)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        cancel_future = executor.submit(
            _cancel_in_thread,
            order.pk,
            customer.user_id,
            barrier,
        )
        expiry_future = executor.submit(
            _finalize_in_thread,
            attempt.pk,
            barrier,
            at=reservation.expires_at,
        )
        cancel_result = cancel_future.result()
        assert expiry_future.result() == PaymentAttempt.Status.FAILED

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert product.stock_quantity == 10
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert attempt.status == PaymentAttempt.Status.FAILED
    assert OrderStatusHistory.objects.filter(order=order).count() == 1
    if cancel_result == "changed":
        assert order.status == Order.Status.CANCELLED
        assert order.refund_status == Order.RefundStatus.NOT_REQUIRED
    else:
        assert cancel_result == "rejected"
        assert order.status == Order.Status.EXPIRED
