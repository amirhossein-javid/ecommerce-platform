from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import Order
from apps.payments.models import PaymentAttempt


@pytest.fixture
def order(db):
    user = User.objects.create_user("payment-model@example.com")
    customer = CustomerProfile.objects.create(user=user)
    return Order.objects.create(
        customer=customer,
        subtotal=Decimal("25.00"),
        discount_total=Decimal("0.00"),
        shipping_total=Decimal("0.00"),
        grand_total=Decimal("25.00"),
        shipping_title="Home",
        shipping_recipient_first_name="Ali",
        shipping_recipient_last_name="Ahmadi",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Historical address",
        shipping_postal_code="1234567890",
    )


def create_attempt(order, reference, **overrides):
    values = {
        "order": order,
        "amount": order.grand_total,
        "currency": "USD",
        "gateway": "test",
        "gateway_reference": reference,
        "payment_url": f"https://payments.example/{reference}",
    }
    values.update(overrides)
    return PaymentAttempt.objects.create(**values)


@pytest.mark.django_db
def test_payment_attempt_snapshots_amount_currency_and_defaults(order):
    attempt = create_attempt(order, "ref-defaults")

    assert attempt.status == PaymentAttempt.Status.PENDING
    assert attempt.amount == Decimal("25.00")
    assert attempt.currency == "USD"
    assert attempt.created_at is not None
    assert str(attempt) == (
        f"Payment attempt {attempt.pk} for order {order.pk} (PENDING)"
    )


@pytest.mark.django_db
def test_database_allows_only_one_pending_attempt_per_order(order):
    create_attempt(order, "ref-first")

    with pytest.raises(IntegrityError), transaction.atomic():
        create_attempt(order, "ref-second")


@pytest.mark.django_db
def test_database_allows_new_pending_attempt_after_failure(order):
    create_attempt(
        order,
        "ref-failed",
        status=PaymentAttempt.Status.FAILED,
    )

    pending = create_attempt(order, "ref-retry")

    assert pending.status == PaymentAttempt.Status.PENDING


@pytest.mark.django_db
def test_uninitialized_pending_attempt_has_stable_unique_idempotency_key(order):
    attempt = create_attempt(
        order,
        None,
        gateway_reference=None,
        payment_url=None,
    )

    assert attempt.idempotency_key is not None
    with pytest.raises(IntegrityError), transaction.atomic():
        create_attempt(
            order,
            None,
            status=PaymentAttempt.Status.FAILED,
            gateway_reference=None,
            payment_url=None,
            idempotency_key=attempt.idempotency_key,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "reference"),
    [
        ({"status": "UNKNOWN"}, "invalid-status"),
        ({"amount": Decimal("-0.01")}, "negative-amount"),
        ({"currency": "EUR"}, "invalid-currency"),
        ({"gateway": ""}, "empty-gateway"),
        ({"gateway_reference": ""}, "ignored"),
        ({"payment_url": ""}, "empty-url"),
    ],
)
def test_database_rejects_invalid_attempt_values(order, overrides, reference):
    with pytest.raises(IntegrityError), transaction.atomic():
        create_attempt(order, reference, **overrides)


@pytest.mark.django_db
def test_gateway_reference_is_unique_within_gateway(order):
    first = create_attempt(
        order,
        "same-reference",
        status=PaymentAttempt.Status.FAILED,
    )
    other_user = User.objects.create_user("other-payment-model@example.com")
    other_customer = CustomerProfile.objects.create(user=other_user)
    other_order = Order.objects.create(
        customer=other_customer,
        subtotal=first.order.subtotal,
        discount_total=first.order.discount_total,
        shipping_total=first.order.shipping_total,
        grand_total=first.order.grand_total,
        shipping_title="Home",
        shipping_recipient_first_name="Ali",
        shipping_recipient_last_name="Ahmadi",
        shipping_recipient_phone_number="+989121234568",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Other historical address",
        shipping_postal_code="1234567891",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        create_attempt(other_order, "same-reference")
