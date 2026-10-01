from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from threading import Barrier, Event, Lock
from time import sleep
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, close_old_connections, transaction
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import InventoryReservation, Order
from apps.orders.services import RESERVATION_LIFETIME
from apps.payments import bale_webhooks
from apps.payments.bale_webhooks import PROCESSING_LEASE
from apps.payments.gateways import (
    PaymentGatewayUnavailable,
    PaymentTransaction,
    TransactionStatus,
)
from apps.payments.models import BaleWebhookUpdate, PaymentAttempt
from apps.products.models import Category, Product

WEBHOOK_URL = reverse("payments:bale-webhook")


class FakeBaleWebhookGateway:
    name = "bale"

    def __init__(
        self,
        *,
        transaction_status=TransactionStatus.PAID,
        inquiry_barrier=None,
        answer_barrier=None,
        answer_started=None,
        answer_release=None,
    ):
        self.transaction_status = transaction_status
        self.transaction_id = None
        self.amount = Decimal("25")
        self.inquiry_barrier = inquiry_barrier
        self.answer_barrier = answer_barrier
        self.answer_started = answer_started
        self.answer_release = answer_release
        self.answers = []
        self.inquiries = []
        self._lock = Lock()
        self.answer_error = None
        self.inquiry_error = None

    def answer_pre_checkout_query(self, **kwargs):
        with self._lock:
            self.answers.append(kwargs)
        if self.answer_started is not None:
            self.answer_started.set()
        if self.answer_barrier is not None:
            self.answer_barrier.wait(timeout=10)
        if self.answer_release is not None:
            self.answer_release.wait(timeout=10)
        if self.answer_error is not None:
            raise self.answer_error

    def inquire_transaction(self, transaction_id):
        with self._lock:
            self.inquiries.append(transaction_id)
        if self.inquiry_barrier is not None:
            self.inquiry_barrier.wait(timeout=10)
        if self.inquiry_error is not None:
            raise self.inquiry_error
        return PaymentTransaction(
            transaction_id=self.transaction_id or transaction_id,
            status=self.transaction_status,
            amount=self.amount,
            user_id=123,
            created_at=1_700_000_000,
        )


def create_bale_payment(*, email=None, stock=10):
    user = User.objects.create_user(email or f"webhook-{uuid4()}@example.com")
    customer = CustomerProfile.objects.create(user=user)
    category = Category.objects.create(name=f"Webhook category {uuid4()}")
    product = Product.objects.create(
        category=category,
        name="Webhook product",
        slug=f"webhook-product-{uuid4()}",
        sku=f"WEBHOOK-{uuid4()}",
        price=Decimal("25"),
        stock_quantity=stock,
        status=Product.Status.ACTIVE,
    )
    order = Order.objects.create(
        customer=customer,
        subtotal=Decimal("25"),
        discount_total=Decimal("0"),
        shipping_total=Decimal("0"),
        grand_total=Decimal("25"),
        shipping_title="Home",
        shipping_recipient_first_name="Ali",
        shipping_recipient_last_name="Ahmadi",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Historical address",
        shipping_postal_code="1234567890",
    )
    reservation = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=2,
        expires_at=timezone.now() + RESERVATION_LIFETIME,
    )
    attempt = PaymentAttempt.objects.create(
        order=order,
        amount=order.grand_total,
        currency="IRR",
        gateway="bale",
        gateway_reference=f"invoice-{uuid4()}",
    )
    return order, product, reservation, attempt


def payload_for(attempt):
    return f"pay:{attempt.idempotency_key.hex}"


def pre_checkout_update(attempt, *, update_id=1, transaction_id="tx-1", **changes):
    query = {
        "id": transaction_id,
        "currency": "IRR",
        "total_amount": 25,
        "invoice_payload": payload_for(attempt),
    }
    query.update(changes)
    return {"update_id": update_id, "pre_checkout_query": query}


def successful_update(attempt, *, update_id=2, transaction_id="tx-1", **changes):
    payment = {
        "currency": "IRR",
        "total_amount": 25,
        "invoice_payload": payload_for(attempt),
        "telegram_payment_charge_id": transaction_id,
        "provider_payment_charge_id": "tracking-1",
    }
    payment.update(changes)
    return {"update_id": update_id, "message": {"successful_payment": payment}}


def configure_gateway(monkeypatch, gateway):
    monkeypatch.setattr("apps.payments.views.get_payment_gateway", lambda: gateway)


def configure_recovery_gateway(monkeypatch, gateway):
    monkeypatch.setattr(
        "apps.payments.management.commands.recover_bale_payments.get_payment_gateway",
        lambda: gateway,
    )


def bind_pre_checkout(client, attempt, gateway, *, update_id=1, transaction_id="tx-1"):
    response = client.post(
        WEBHOOK_URL,
        pre_checkout_update(
            attempt,
            update_id=update_id,
            transaction_id=transaction_id,
        ),
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert gateway.answers[-1]["ok"] is True
    attempt.refresh_from_db()
    assert attempt.provider_transaction_id == transaction_id


def expire_reservation(reservation):
    now = timezone.now()
    InventoryReservation.objects.filter(pk=reservation.pk).update(
        created_at=now - RESERVATION_LIFETIME,
        expires_at=now - timedelta(seconds=1),
    )


@pytest.mark.django_db
def test_valid_pre_checkout_is_approved_without_finalizing(monkeypatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)

    response = APIClient().post(
        WEBHOOK_URL,
        pre_checkout_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"ok": True}
    assert gateway.answers == [
        {
            "pre_checkout_query_id": "tx-1",
            "ok": True,
            "error_message": None,
        }
    ]
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert attempt.provider_transaction_id == "tx-1"
    assert reservation.status == InventoryReservation.Status.ACTIVE
    assert product.stock_quantity == 10


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes",
    [
        {"total_amount": 26},
        {"currency": "USD"},
        {"invoice_payload": "not-a-payment-payload"},
        {"invoice_payload": f"pay:{uuid4().hex}"},
    ],
)
def test_invalid_pre_checkout_is_rejected_safely(monkeypatch, changes):
    _, _, _, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)

    response = APIClient().post(
        WEBHOOK_URL,
        pre_checkout_update(attempt, **changes),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert gateway.answers[0]["ok"] is False
    assert gateway.answers[0]["error_message"] == "Payment cannot be completed."
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert attempt.provider_transaction_id is None


@pytest.mark.django_db
@pytest.mark.parametrize("invalid_state", ["expired", "released", "failed"])
def test_pre_checkout_rejects_unpayable_local_state(
    monkeypatch,
    invalid_state,
):
    order, _, reservation, attempt = create_bale_payment()
    if invalid_state == "expired":
        expire_reservation(reservation)
    elif invalid_state == "released":
        reservation.status = InventoryReservation.Status.RELEASED
        reservation.save(update_fields=("status", "updated_at"))
    else:
        attempt.status = PaymentAttempt.Status.FAILED
        attempt.save(update_fields=("status", "updated_at"))
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)

    response = APIClient().post(
        WEBHOOK_URL,
        pre_checkout_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert gateway.answers[0]["ok"] is False
    order.refresh_from_db()
    reservation.refresh_from_db()
    if invalid_state == "expired":
        assert order.status == Order.Status.EXPIRED
        assert reservation.status == InventoryReservation.Status.RELEASED


@pytest.mark.django_db
def test_pre_checkout_answer_failure_is_retryable_and_sanitized(monkeypatch):
    _, _, _, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    secret = "bot-token upstream response"
    gateway.answer_error = PaymentGatewayUnavailable(secret)
    configure_gateway(monkeypatch, gateway)

    response = APIClient().post(
        WEBHOOK_URL,
        pre_checkout_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"ok": True}
    assert secret not in response.content.decode()
    assert BaleWebhookUpdate.objects.get(update_id=1).status == (
        BaleWebhookUpdate.Status.PENDING
    )
    attempt.refresh_from_db()
    assert attempt.provider_transaction_id is None
    assert attempt.pre_checkout_transaction_id is None


@pytest.mark.django_db
def test_failed_pre_checkout_answer_does_not_poison_later_identifier(monkeypatch):
    _, _, _, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    gateway.answer_error = PaymentGatewayUnavailable("temporary")
    configure_gateway(monkeypatch, gateway)
    client = APIClient()

    first = client.post(
        WEBHOOK_URL,
        pre_checkout_update(attempt, update_id=1, transaction_id="tx-failed"),
        format="json",
    )
    gateway.answer_error = None
    second = client.post(
        WEBHOOK_URL,
        pre_checkout_update(attempt, update_id=2, transaction_id="tx-accepted"),
        format="json",
    )

    assert first.status_code == second.status_code == status.HTTP_200_OK
    attempt.refresh_from_db()
    assert attempt.provider_transaction_id == "tx-accepted"
    assert attempt.pre_checkout_transaction_id is None
    assert BaleWebhookUpdate.objects.get(update_id=1).status == (
        BaleWebhookUpdate.Status.PENDING
    )
    assert BaleWebhookUpdate.objects.get(update_id=2).status == (
        BaleWebhookUpdate.Status.PROCESSED
    )


@pytest.mark.django_db
def test_paid_inquiry_atomically_finalizes_bale_payment(monkeypatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)

    response = client.post(
        WEBHOOK_URL,
        successful_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert gateway.inquiries == ["tx-1"]
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert attempt.provider_transaction_id == "tx-1"
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert product.stock_quantity == 8


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("provider_status", "expected_http", "expected_attempt"),
    [
        (TransactionStatus.PENDING, status.HTTP_200_OK, "PENDING"),
        (TransactionStatus.FAILED, status.HTTP_200_OK, "FAILED"),
        (TransactionStatus.REJECTED, status.HTTP_200_OK, "FAILED"),
    ],
)
def test_non_paid_inquiry_never_finalizes_order(
    monkeypatch,
    provider_status,
    expected_http,
    expected_attempt,
):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway(transaction_status=provider_status)
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)

    response = client.post(
        WEBHOOK_URL,
        successful_update(attempt),
        format="json",
    )

    assert response.status_code == expected_http
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert attempt.status == expected_attempt
    assert reservation.status == InventoryReservation.Status.ACTIVE
    assert product.stock_quantity == 10
    expected_update_status = (
        BaleWebhookUpdate.Status.PENDING
        if provider_status == TransactionStatus.PENDING
        else BaleWebhookUpdate.Status.PROCESSED
    )
    assert BaleWebhookUpdate.objects.get(update_id=2).status == expected_update_status


@pytest.mark.django_db
@pytest.mark.parametrize("mismatch", ["amount", "transaction_id"])
def test_inquiry_mismatch_does_not_mutate_commerce_state(monkeypatch, mismatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)
    if mismatch == "amount":
        gateway.amount = Decimal("26")
    else:
        gateway.transaction_id = "different-transaction"

    response = client.post(
        WEBHOOK_URL,
        successful_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        BaleWebhookUpdate.objects.get(update_id=2).status
        == BaleWebhookUpdate.Status.REJECTED
    )
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert reservation.status == InventoryReservation.Status.ACTIVE
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_successful_payment_requires_pre_checkout_transaction_binding(monkeypatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)

    response = APIClient().post(
        WEBHOOK_URL,
        successful_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        BaleWebhookUpdate.objects.get(update_id=2).status
        == BaleWebhookUpdate.Status.REJECTED
    )
    assert gateway.inquiries == []
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert reservation.status == InventoryReservation.Status.ACTIVE
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_duplicate_update_id_is_acknowledged_without_reprocessing(monkeypatch):
    _, _, _, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    update = pre_checkout_update(attempt, update_id=77)

    first = client.post(WEBHOOK_URL, update, format="json")
    second = client.post(WEBHOOK_URL, update, format="json")

    assert first.status_code == second.status_code == status.HTTP_200_OK
    assert len(gateway.answers) == 1
    assert BaleWebhookUpdate.objects.filter(update_id=77).count() == 1


@pytest.mark.django_db
def test_duplicate_successful_payment_deducts_stock_once(monkeypatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)

    first = client.post(
        WEBHOOK_URL,
        successful_update(attempt, update_id=2),
        format="json",
    )
    second = client.post(
        WEBHOOK_URL,
        successful_update(attempt, update_id=3),
        format="json",
    )

    assert first.status_code == second.status_code == status.HTTP_200_OK
    assert gateway.inquiries == ["tx-1"]
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert product.stock_quantity == 8


@pytest.mark.django_db
def test_provider_transaction_cannot_be_reused_across_attempts(monkeypatch):
    _, _, _, first_attempt = create_bale_payment()
    second_order, second_product, second_reservation, second_attempt = (
        create_bale_payment()
    )
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, first_attempt, gateway, transaction_id="shared-tx")

    reused = client.post(
        WEBHOOK_URL,
        pre_checkout_update(
            second_attempt,
            update_id=2,
            transaction_id="shared-tx",
        ),
        format="json",
    )

    assert reused.status_code == status.HTTP_200_OK
    assert gateway.answers[-1]["ok"] is False
    second_attempt.refresh_from_db()
    second_order.refresh_from_db()
    second_product.refresh_from_db()
    second_reservation.refresh_from_db()
    assert second_attempt.provider_transaction_id is None
    assert second_order.status == Order.Status.PENDING_PAYMENT
    assert second_product.stock_quantity == 10
    assert second_reservation.status == InventoryReservation.Status.ACTIVE

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            second_attempt.provider_transaction_id = "shared-tx"
            second_attempt.save(update_fields=("provider_transaction_id",))


@pytest.mark.django_db
def test_successful_payment_after_expiry_expires_without_stock_deduction(monkeypatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)
    expire_reservation(reservation)

    response = client.post(
        WEBHOOK_URL,
        successful_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.EXPIRED
    assert attempt.status == PaymentAttempt.Status.FAILED
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_webhook_rejects_malformed_json_and_structural_input(monkeypatch):
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()

    malformed = client.generic(
        "POST",
        WEBHOOK_URL,
        data="{not-json",
        content_type="application/json",
    )
    structural = client.post(
        WEBHOOK_URL,
        {"update_id": "not-an-integer", "pre_checkout_query": {}},
        format="json",
    )

    assert malformed.status_code == status.HTTP_400_BAD_REQUEST
    assert structural.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        malformed.json()
        == structural.json()
        == {"detail": "Invalid Bale payment update."}
    )
    assert gateway.answers == []


@pytest.mark.django_db
def test_non_payment_update_is_acknowledged_without_state_change(monkeypatch):
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)

    response = APIClient().post(
        WEBHOOK_URL,
        {"update_id": 99, "message": {}},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"ok": True}
    assert gateway.answers == []
    assert gateway.inquiries == []
    assert not BaleWebhookUpdate.objects.filter(update_id=99).exists()


@pytest.mark.django_db
def test_successful_payment_gateway_error_is_sanitized_and_retryable(monkeypatch):
    _, _, _, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)
    secret = "wallet token and raw upstream body"
    gateway.inquiry_error = PaymentGatewayUnavailable(secret)

    response = client.post(
        WEBHOOK_URL,
        successful_update(attempt),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"ok": True}
    assert secret not in response.content.decode()
    assert (
        BaleWebhookUpdate.objects.get(update_id=2).status
        == BaleWebhookUpdate.Status.PENDING
    )


def post_successful_update_in_thread(attempt_id, update_id, gateway):
    close_old_connections()
    try:
        attempt = PaymentAttempt.objects.get(pk=attempt_id)
        response = APIClient().post(
            WEBHOOK_URL,
            successful_update(attempt, update_id=update_id),
            format="json",
        )
        return response.status_code
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_successful_updates_deduct_stock_exactly_once(monkeypatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway(inquiry_barrier=Barrier(2))
    configure_gateway(monkeypatch, gateway)
    bind_pre_checkout(APIClient(), attempt, gateway)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                post_successful_update_in_thread,
                attempt.pk,
                update_id,
                gateway,
            )
            for update_id in (2, 3)
        ]
        results = [future.result(timeout=15) for future in futures]

    assert results == [status.HTTP_200_OK, status.HTTP_200_OK]
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert product.stock_quantity == 8
    assert len(gateway.inquiries) == 2


def post_update_in_thread(update):
    close_old_connections()
    try:
        response = APIClient().post(WEBHOOK_URL, update, format="json")
        return response.status_code
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_different_pre_checkout_ids_accept_only_one(monkeypatch):
    _, _, _, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway(answer_barrier=Barrier(2))
    configure_gateway(monkeypatch, gateway)
    updates = [
        pre_checkout_update(
            attempt,
            update_id=update_id,
            transaction_id=transaction_id,
        )
        for update_id, transaction_id in ((10, "tx-first"), (11, "tx-second"))
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(post_update_in_thread, updates))

    assert results == [status.HTTP_200_OK, status.HTTP_200_OK]
    assert sorted(answer["ok"] for answer in gateway.answers) == [False, True]
    attempt.refresh_from_db()
    assert attempt.provider_transaction_id in {"tx-first", "tx-second"}
    assert attempt.pre_checkout_transaction_id is None
    assert set(
        BaleWebhookUpdate.objects.filter(update_id__in=(10, 11)).values_list(
            "status", flat=True
        )
    ) == {BaleWebhookUpdate.Status.PROCESSED}


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_update_id_is_processed_once(monkeypatch):
    _, _, _, attempt = create_bale_payment()
    answer_started = Event()
    answer_release = Event()
    gateway = FakeBaleWebhookGateway(
        answer_started=answer_started,
        answer_release=answer_release,
    )
    configure_gateway(monkeypatch, gateway)
    update = pre_checkout_update(attempt, update_id=20)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(post_update_in_thread, update)
        assert answer_started.wait(timeout=5)
        second = executor.submit(post_update_in_thread, update)
        assert second.result(timeout=5) == status.HTTP_200_OK
        answer_release.set()
        assert first.result(timeout=10) == status.HTTP_200_OK

    assert len(gateway.answers) == 1
    assert BaleWebhookUpdate.objects.get(update_id=20).status == (
        BaleWebhookUpdate.Status.PROCESSED
    )


@pytest.mark.django_db(transaction=True)
def test_pre_checkout_waiting_on_order_lock_rechecks_expiry(monkeypatch):
    order, product, reservation, attempt = create_bale_payment(stock=3)
    InventoryReservation.objects.filter(pk=reservation.pk).update(
        expires_at=timezone.now() + timedelta(seconds=1)
    )
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    update = pre_checkout_update(attempt, update_id=30)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            Order.objects.select_for_update().get(pk=order.pk)
            future = executor.submit(post_update_in_thread, update)
            sleep(1.2)
        assert future.result(timeout=10) == status.HTTP_200_OK

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert gateway.answers[-1]["ok"] is False
    assert order.status == Order.Status.EXPIRED
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert attempt.status == PaymentAttempt.Status.FAILED
    assert attempt.provider_transaction_id is None
    assert product.stock_quantity == 3


@pytest.mark.django_db
def test_temporary_inquiry_failure_is_recovered_locally(monkeypatch):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    configure_recovery_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)
    gateway.inquiry_error = PaymentGatewayUnavailable("temporary")

    response = client.post(
        WEBHOOK_URL,
        successful_update(attempt, update_id=40),
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert BaleWebhookUpdate.objects.get(update_id=40).status == (
        BaleWebhookUpdate.Status.PENDING
    )

    gateway.inquiry_error = None
    call_command("recover_bale_payments")

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert BaleWebhookUpdate.objects.get(update_id=40).status == (
        BaleWebhookUpdate.Status.PROCESSED
    )
    assert order.status == Order.Status.PAID
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert product.stock_quantity == 8


@pytest.mark.django_db
def test_pending_inquiry_is_later_paid_by_local_recovery(monkeypatch):
    order, product, _, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway(transaction_status=TransactionStatus.PENDING)
    configure_gateway(monkeypatch, gateway)
    configure_recovery_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)

    response = client.post(
        WEBHOOK_URL,
        successful_update(attempt, update_id=41),
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert BaleWebhookUpdate.objects.get(update_id=41).status == (
        BaleWebhookUpdate.Status.PENDING
    )

    gateway.transaction_status = TransactionStatus.PAID
    call_command("recover_bale_payments")

    order.refresh_from_db()
    product.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert product.stock_quantity == 8
    assert BaleWebhookUpdate.objects.get(update_id=41).status == (
        BaleWebhookUpdate.Status.PROCESSED
    )


def make_processing_record_stale(update_id):
    BaleWebhookUpdate.objects.filter(update_id=update_id).update(
        processing_started_at=timezone.now() - PROCESSING_LEASE - timedelta(seconds=1)
    )


@pytest.mark.django_db
def test_recovery_after_finalization_before_receipt_does_not_deduct_twice(
    monkeypatch,
):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway()
    configure_gateway(monkeypatch, gateway)
    configure_recovery_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)
    original_finish = bale_webhooks._finish_bale_update

    def crash_before_receipt(**kwargs):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(bale_webhooks, "_finish_bale_update", crash_before_receipt)
    with pytest.raises(RuntimeError, match="simulated crash"):
        client.post(
            WEBHOOK_URL,
            successful_update(attempt, update_id=50),
            format="json",
        )
    monkeypatch.setattr(bale_webhooks, "_finish_bale_update", original_finish)

    order.refresh_from_db()
    product.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert product.stock_quantity == 8
    make_processing_record_stale(50)

    call_command("recover_bale_payments")

    product.refresh_from_db()
    reservation.refresh_from_db()
    assert product.stock_quantity == 8
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert BaleWebhookUpdate.objects.get(update_id=50).status == (
        BaleWebhookUpdate.Status.PROCESSED
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "failed_status", [TransactionStatus.FAILED, TransactionStatus.REJECTED]
)
def test_failed_transition_is_recovered_after_receipt_marking_failure(
    monkeypatch,
    failed_status,
):
    order, product, reservation, attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway(transaction_status=failed_status)
    configure_gateway(monkeypatch, gateway)
    configure_recovery_gateway(monkeypatch, gateway)
    client = APIClient()
    bind_pre_checkout(client, attempt, gateway)
    original_finish = bale_webhooks._finish_bale_update

    monkeypatch.setattr(
        bale_webhooks,
        "_finish_bale_update",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("simulated crash")),
    )
    with pytest.raises(RuntimeError, match="simulated crash"):
        client.post(
            WEBHOOK_URL,
            successful_update(attempt, update_id=51),
            format="json",
        )
    monkeypatch.setattr(bale_webhooks, "_finish_bale_update", original_finish)
    make_processing_record_stale(51)

    call_command("recover_bale_payments")

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert attempt.status == PaymentAttempt.Status.FAILED
    assert product.stock_quantity == 10
    assert reservation.status == InventoryReservation.Status.ACTIVE
    assert BaleWebhookUpdate.objects.get(update_id=51).status == (
        BaleWebhookUpdate.Status.PROCESSED
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_transaction_id_cannot_bind_two_attempts(monkeypatch):
    _, _, _, first_attempt = create_bale_payment()
    _, _, _, second_attempt = create_bale_payment()
    gateway = FakeBaleWebhookGateway(answer_barrier=Barrier(2))
    configure_gateway(monkeypatch, gateway)
    updates = [
        pre_checkout_update(
            attempt,
            update_id=update_id,
            transaction_id="shared-concurrent-tx",
        )
        for attempt, update_id in ((first_attempt, 60), (second_attempt, 61))
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(post_update_in_thread, updates))

    assert results == [status.HTTP_200_OK, status.HTTP_200_OK]
    assert sorted(answer["ok"] for answer in gateway.answers) == [False, True]
    bound = PaymentAttempt.objects.filter(
        provider_transaction_id="shared-concurrent-tx"
    )
    assert bound.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "configured_url",
    [
        "https://payments.example-shop.com/api/v1/payments/bale/webhook/",
        "https://payments.example-shop.com:443/api/v1/payments/bale/webhook/",
        "https://payments.example-shop.com:88/api/v1/payments/bale/webhook/",
    ],
)
def test_set_bale_webhook_command_accepts_public_https_supported_ports(
    monkeypatch,
    configured_url,
):
    calls = []
    monkeypatch.setattr(
        "apps.payments.management.commands.set_bale_webhook.BaleGateway.set_webhook",
        lambda self, url: calls.append(url),
    )
    stdout = StringIO()

    with override_settings(BALE_WEBHOOK_URL=configured_url):
        call_command("set_bale_webhook", stdout=stdout)

    assert calls == [configured_url]
    assert "Bale webhook registered." in stdout.getvalue()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "configured_url",
    [
        "",
        "http://payments.example-shop.com/api/v1/payments/bale/webhook/",
        "https://user:password@payments.example-shop.com/api/v1/payments/bale/webhook/",
        "https://payments.example-shop.com/api/v1/payments/bale/webhook/#fragment",
        "https://payments.example-shop.com:8443/api/v1/payments/bale/webhook/",
        "https://payments.example-shop.com:not-a-port/api/v1/payments/bale/webhook/",
        "https://localhost/api/v1/payments/bale/webhook/",
        "https://127.0.0.1/api/v1/payments/bale/webhook/",
        "https://[::1]/api/v1/payments/bale/webhook/",
        "https://example.com/api/v1/payments/bale/webhook/",
        "https://shop.example.net/api/v1/payments/bale/webhook/",
        "https://payments.example-shop.com/api/v1/payments/bale/webhook",
        "https://payments.example-shop.com/wrong-webhook/",
    ],
)
def test_set_bale_webhook_command_rejects_invalid_configuration(configured_url):
    with override_settings(BALE_WEBHOOK_URL=configured_url):
        with pytest.raises(CommandError, match="public HTTPS Bale webhook URL"):
            call_command("set_bale_webhook")


@pytest.mark.django_db
@override_settings(
    BALE_WEBHOOK_URL=("https://payments.example-shop.com/api/v1/payments/bale/webhook/")
)
def test_set_bale_webhook_command_sanitizes_gateway_errors(monkeypatch):
    secret = "bot token and provider response"

    def fail(self, url):
        raise PaymentGatewayUnavailable(secret)

    monkeypatch.setattr(
        "apps.payments.management.commands.set_bale_webhook.BaleGateway.set_webhook",
        fail,
    )

    with pytest.raises(CommandError, match="Bale webhook registration failed") as exc:
        call_command("set_bale_webhook")

    assert secret not in str(exc.value)


@pytest.mark.django_db
def test_bale_webhook_is_documented_as_unauthenticated():
    response = APIClient().get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    operation = response.json()["paths"]["/api/v1/payments/bale/webhook/"]["post"]
    assert operation.get("security", []) == []
    assert {"200", "400"} <= operation["responses"].keys()
