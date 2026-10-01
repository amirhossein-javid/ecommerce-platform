from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from threading import Barrier, Event, Lock
from time import sleep
from uuid import uuid4

import pytest
from django.db import close_old_connections, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import InventoryReservation, Order
from apps.orders.services import RESERVATION_LIFETIME
from apps.payments.gateways import (
    PaymentGatewayUnavailable,
    PaymentInitiation,
    PaymentVerification,
    VerificationStatus,
)
from apps.payments.models import PaymentAttempt
from apps.payments.services import (
    PaymentVerificationInvalid,
    PaymentWindowExpired,
    initiate_order_payment,
    verify_order_payment,
)
from apps.products.models import Category, Product


class FakeGateway:
    name = "fake"

    def __init__(
        self,
        verification_status=VerificationStatus.SUCCESS,
        initiation_barrier=None,
        verification_event=None,
    ):
        self.verification_status = verification_status
        self.initiation_barrier = initiation_barrier
        self.verification_event = verification_event
        self.initiations = []
        self.verifications = []
        self._lock = Lock()

    def initiate(self, *, order_id, amount, currency, idempotency_key):
        reference = f"fake-{idempotency_key}"
        with self._lock:
            self.initiations.append((order_id, amount, currency, idempotency_key))
        if self.initiation_barrier is not None:
            self.initiation_barrier.wait(timeout=10)
        return PaymentInitiation(
            gateway_reference=reference,
            payment_url=f"https://payments.example/{reference}",
        )

    def verify(self, *, gateway_reference, callback_data):
        with self._lock:
            self.verifications.append((gateway_reference, callback_data))
        if self.verification_event is not None:
            self.verification_event.set()
        return PaymentVerification(
            status=self.verification_status,
            gateway_reference=gateway_reference,
            amount=Decimal("25.00"),
            currency="IRR",
        )


class AmbiguousOnceGateway(FakeGateway):
    def initiate(self, *, order_id, amount, currency, idempotency_key):
        reference = f"fake-{idempotency_key}"
        with self._lock:
            self.initiations.append((order_id, amount, currency, idempotency_key))
            call_count = len(self.initiations)
        if call_count == 1:
            raise PaymentGatewayUnavailable("Ambiguous gateway timeout.")
        return PaymentInitiation(
            gateway_reference=reference,
            payment_url=f"https://payments.example/{reference}",
        )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def gateway(monkeypatch):
    gateway = FakeGateway()
    monkeypatch.setattr(
        "apps.payments.services.get_payment_gateway",
        lambda: gateway,
    )
    return gateway


@pytest.fixture
def customer(db):
    return create_customer("payment-customer@example.com")


@pytest.fixture
def payable_order(customer):
    category = Category.objects.create(name=f"Payment category {uuid4()}")
    product = Product.objects.create(
        category=category,
        name="Payable product",
        slug=f"payable-{uuid4()}",
        sku=f"PAY-{uuid4()}",
        price=Decimal("12.00"),
        stock_quantity=10,
        status=Product.Status.ACTIVE,
    )
    order = create_order(customer)
    reservation = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=2,
        expires_at=timezone.now() + RESERVATION_LIFETIME,
    )
    return order, product, reservation


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
        shipping_recipient_first_name="Ali",
        shipping_recipient_last_name="Ahmadi",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Historical address",
        shipping_postal_code="1234567890",
    )


def initiate_url(order):
    return reverse("payments:payment-initiate", kwargs={"order_id": order.pk})


def verify_url(attempt):
    return reverse(
        "payments:payment-verify",
        kwargs={"order_id": attempt.order_id, "payment_id": attempt.pk},
    )


def expire_reservation(reservation):
    now = timezone.now()
    InventoryReservation.objects.filter(pk=reservation.pk).update(
        created_at=now - RESERVATION_LIFETIME,
        expires_at=now - timedelta(seconds=1),
    )


@pytest.mark.django_db
def test_payment_initiation_requires_authentication(api_client, payable_order):
    order, _, _ = payable_order

    response = api_client.post(initiate_url(order), {}, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_only_owner_can_initiate_without_order_disclosure(
    api_client,
    payable_order,
    gateway,
):
    order, _, _ = payable_order
    other = create_customer("other-payment@example.com")
    api_client.force_authenticate(user=other.user)

    cross_customer = api_client.post(initiate_url(order), {}, format="json")
    unknown = api_client.post(
        reverse("payments:payment-initiate", kwargs={"order_id": order.pk + 99999}),
        {},
        format="json",
    )

    assert cross_customer.status_code == status.HTTP_404_NOT_FOUND
    assert cross_customer.json() == unknown.json()
    assert gateway.initiations == []


@pytest.mark.django_db
def test_user_without_customer_profile_fails_safely(
    api_client,
    payable_order,
    gateway,
):
    order, _, _ = payable_order
    user = User.objects.create_user("staff-payment@example.com")
    api_client.force_authenticate(user=user)

    response = api_client.post(initiate_url(order), {}, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Customer profile not found."}
    assert gateway.initiations == []


@pytest.mark.django_db
def test_only_pending_payment_orders_can_be_initiated(
    api_client,
    payable_order,
    gateway,
):
    order, _, _ = payable_order
    order.status = Order.Status.PAID
    order.save(update_fields=("status", "updated_at"))
    api_client.force_authenticate(user=order.customer.user)

    response = api_client.post(initiate_url(order), {}, format="json")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert PaymentAttempt.objects.filter(order=order).exists() is False
    assert gateway.initiations == []


@pytest.mark.django_db
def test_non_bale_initiation_does_not_expose_internal_gateway_reference(
    api_client,
    payable_order,
    gateway,
):
    order, _, _ = payable_order
    api_client.force_authenticate(user=order.customer.user)

    response = api_client.post(
        initiate_url(order),
        {"amount": "0.01", "currency": "EUR"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    attempt = PaymentAttempt.objects.get(pk=response.json()["id"])
    assert attempt.amount == order.grand_total == Decimal("25.00")
    assert attempt.currency == "IRR"
    assert len(gateway.initiations) == 1
    initiated_order, initiated_amount, initiated_currency, key = gateway.initiations[0]
    assert (initiated_order, initiated_amount, initiated_currency) == (
        order.pk,
        Decimal("25.00"),
        "IRR",
    )
    assert key == attempt.idempotency_key
    assert response.json()["amount"] == "25"
    assert response.json()["currency"] == "IRR"
    assert response.json()["payment_identifier"] is None
    assert "gateway" not in response.json()
    assert "gateway_reference" not in response.json()
    assert "idempotency_key" not in response.json()
    assert "provider_transaction_id" not in response.json()
    assert "pre_checkout_transaction_id" not in response.json()


@pytest.mark.django_db
def test_duplicate_initiation_returns_existing_pending_attempt(
    api_client,
    payable_order,
    gateway,
):
    order, _, _ = payable_order
    api_client.force_authenticate(user=order.customer.user)

    first = api_client.post(initiate_url(order), {}, format="json")
    second = api_client.post(initiate_url(order), {}, format="json")

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_200_OK
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["payment_url"] == second.json()["payment_url"]
    assert first.json()["payment_identifier"] is None
    assert second.json()["payment_identifier"] is None
    assert second.json()["payment_url"] is not None
    assert PaymentAttempt.objects.filter(order=order).count() == 1
    assert len(gateway.initiations) == 1


@pytest.mark.django_db
def test_ambiguous_gateway_timeout_retries_same_durable_idempotency_key(
    payable_order,
):
    order, _, _ = payable_order
    gateway = AmbiguousOnceGateway()

    with pytest.raises(PaymentGatewayUnavailable, match="Ambiguous"):
        initiate_order_payment(order=order, gateway=gateway)

    pending = PaymentAttempt.objects.get(order=order)
    assert pending.status == PaymentAttempt.Status.PENDING
    assert pending.gateway_reference is None
    first_key = pending.idempotency_key

    retried, payment_url, created = initiate_order_payment(
        order=order,
        gateway=gateway,
    )

    assert created is False
    assert retried.pk == pending.pk
    assert retried.idempotency_key == first_key
    assert payment_url == f"https://payments.example/fake-{first_key}"
    assert [call[3] for call in gateway.initiations] == [first_key, first_key]
    assert PaymentAttempt.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_initiation_does_not_expose_payment_gateway_error_details(
    api_client,
    payable_order,
    gateway,
    monkeypatch,
):
    order, _, _ = payable_order
    sensitive_detail = (
        "merchant_secret=top-secret; gateway_reference=internal-reference; "
        "upstream_body=private-response"
    )

    def raise_gateway_error(**kwargs):
        raise PaymentGatewayUnavailable(sensitive_detail)

    monkeypatch.setattr(gateway, "initiate", raise_gateway_error)
    api_client.force_authenticate(user=order.customer.user)

    response = api_client.post(initiate_url(order), {}, format="json")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Payment gateway is temporarily unavailable."}
    assert sensitive_detail not in response.content.decode()


@pytest.mark.django_db
def test_only_owner_can_verify_without_payment_disclosure(
    api_client,
    payable_order,
    gateway,
):
    order, _, _ = payable_order
    attempt, _, _ = initiate_order_payment(order=order, gateway=gateway)
    other = create_customer("other-verifier@example.com")
    api_client.force_authenticate(user=other.user)

    cross_customer = api_client.post(
        verify_url(attempt),
        {"callback_data": {}},
        format="json",
    )
    unknown = api_client.post(
        reverse(
            "payments:payment-verify",
            kwargs={
                "order_id": order.pk + 99999,
                "payment_id": attempt.pk + 99999,
            },
        ),
        {"callback_data": {}},
        format="json",
    )

    assert cross_customer.status_code == status.HTTP_404_NOT_FOUND
    assert cross_customer.json() == unknown.json()
    assert gateway.verifications == []


@pytest.mark.django_db
def test_verification_does_not_expose_payment_gateway_error_details(
    api_client,
    payable_order,
    gateway,
    monkeypatch,
):
    order, _, _ = payable_order
    attempt, _, _ = initiate_order_payment(order=order, gateway=gateway)
    sensitive_detail = (
        "network_error=connection-refused; merchant_id=private-merchant; "
        "gateway_reference=internal-reference"
    )

    def raise_gateway_error(**kwargs):
        raise PaymentGatewayUnavailable(sensitive_detail)

    monkeypatch.setattr(gateway, "verify", raise_gateway_error)
    api_client.force_authenticate(user=order.customer.user)

    response = api_client.post(
        verify_url(attempt),
        {"callback_data": {"untrusted": "value"}},
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Payment gateway is temporarily unavailable."}
    assert sensitive_detail not in response.content.decode()


@pytest.mark.django_db
def test_failed_verification_allows_retry_while_order_remains_payable(
    api_client,
    payable_order,
    gateway,
):
    order, product, reservation = payable_order
    api_client.force_authenticate(user=order.customer.user)
    first_response = api_client.post(initiate_url(order), {}, format="json")
    first = PaymentAttempt.objects.get(pk=first_response.json()["id"])
    gateway.verification_status = VerificationStatus.FAILED

    failed = api_client.post(
        verify_url(first),
        {"callback_data": {"untrusted": "value"}},
        format="json",
    )
    retry = api_client.post(initiate_url(order), {}, format="json")

    assert failed.status_code == status.HTTP_200_OK
    assert failed.json()["status"] == PaymentAttempt.Status.FAILED
    assert retry.status_code == status.HTTP_201_CREATED
    assert retry.json()["id"] != first.pk
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT
    assert product.stock_quantity == 10
    assert reservation.status == InventoryReservation.Status.ACTIVE


@pytest.mark.django_db
def test_expired_initiation_expires_order_releases_reservation_and_fails_pending(
    api_client,
    payable_order,
    gateway,
):
    order, product, reservation = payable_order
    pending = PaymentAttempt.objects.create(
        order=order,
        amount=order.grand_total,
        currency="IRR",
        gateway=gateway.name,
        gateway_reference="existing-expired",
        payment_url="https://payments.example/existing-expired",
    )
    expire_reservation(reservation)
    api_client.force_authenticate(user=order.customer.user)

    response = api_client.post(initiate_url(order), {}, format="json")

    assert response.status_code == status.HTTP_409_CONFLICT
    order.refresh_from_db()
    reservation.refresh_from_db()
    pending.refresh_from_db()
    product.refresh_from_db()
    assert order.status == Order.Status.EXPIRED
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert pending.status == PaymentAttempt.Status.FAILED
    assert product.stock_quantity == 10
    assert gateway.initiations == []


@pytest.mark.django_db
def test_successful_verification_finalizes_order_and_stock_once(
    api_client,
    payable_order,
    gateway,
):
    order, product, reservation = payable_order
    api_client.force_authenticate(user=order.customer.user)
    initiated = api_client.post(initiate_url(order), {}, format="json")
    attempt = PaymentAttempt.objects.get(pk=initiated.json()["id"])

    first = api_client.post(
        verify_url(attempt),
        {"callback_data": {"opaque": "return-data"}},
        format="json",
    )
    second = api_client.post(
        verify_url(attempt),
        {"callback_data": {"opaque": "duplicate"}},
        format="json",
    )

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert first.json()["status"] == PaymentAttempt.Status.SUCCESS
    assert second.json()["status"] == PaymentAttempt.Status.SUCCESS
    assert first.json()["payment_identifier"] is None
    assert second.json()["payment_identifier"] is None
    assert "gateway_reference" not in first.json()
    assert "idempotency_key" not in first.json()
    assert "provider_transaction_id" not in first.json()
    assert "pre_checkout_transaction_id" not in first.json()
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert product.stock_quantity == 8
    assert reservation.status == InventoryReservation.Status.CONSUMED
    assert len(gateway.verifications) == 1


@pytest.mark.django_db
def test_verification_rejects_mismatched_verified_amount_without_mutation(
    payable_order,
    gateway,
    monkeypatch,
):
    order, product, reservation = payable_order
    attempt, _, _ = initiate_order_payment(order=order, gateway=gateway)
    original_verify = gateway.verify

    def wrong_amount(**kwargs):
        return replace(original_verify(**kwargs), amount=Decimal("24.00"))

    monkeypatch.setattr(gateway, "verify", wrong_amount)

    with pytest.raises(PaymentVerificationInvalid, match="amount does not match"):
        verify_order_payment(attempt=attempt, callback_data={}, gateway=gateway)

    attempt.refresh_from_db()
    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert order.status == Order.Status.PENDING_PAYMENT
    assert product.stock_quantity == 10
    assert reservation.status == InventoryReservation.Status.ACTIVE


@pytest.mark.django_db
def test_success_after_expiry_cannot_pay_or_deduct_stock(payable_order, gateway):
    order, product, reservation = payable_order
    attempt, _, _ = initiate_order_payment(order=order, gateway=gateway)
    expire_reservation(reservation)

    result = verify_order_payment(
        attempt=attempt,
        callback_data={"opaque": "success"},
        gateway=gateway,
    )

    order.refresh_from_db()
    product.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert result.status == PaymentAttempt.Status.FAILED
    assert attempt.status == PaymentAttempt.Status.FAILED
    assert order.status == Order.Status.EXPIRED
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert product.stock_quantity == 10


def _initiate_in_thread(order_id, gateway, barrier):
    close_old_connections()
    try:
        order = Order.objects.get(pk=order_id)
        barrier.wait()
        attempt, _, created = initiate_order_payment(order=order, gateway=gateway)
        return attempt.pk, created
    finally:
        close_old_connections()


def _initiate_after_signal(order_id, gateway, started):
    close_old_connections()
    try:
        order = Order.objects.get(pk=order_id)
        started.set()
        try:
            initiate_order_payment(order=order, gateway=gateway)
        except PaymentWindowExpired:
            return "expired"
        return "initiated"
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_initiation_waiting_on_order_lock_rechecks_expiry_after_lock():
    customer = create_customer("initiation-expiry-race@example.com")
    category = Category.objects.create(name="Initiation expiry race")
    product = Product.objects.create(
        category=category,
        name="Initiation expiry product",
        slug="initiation-expiry-product",
        sku="INITIATION-EXPIRY",
        price=Decimal("25.00"),
        stock_quantity=2,
        status=Product.Status.ACTIVE,
    )
    order = create_order(customer)
    reservation = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() + timedelta(seconds=1),
    )
    gateway = FakeGateway()
    started = Event()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            Order.objects.select_for_update().get(pk=order.pk)
            future = executor.submit(
                _initiate_after_signal,
                order.pk,
                gateway,
                started,
            )
            assert started.wait(timeout=5)
            sleep(1.2)
        result = future.result(timeout=10)

    order.refresh_from_db()
    reservation.refresh_from_db()
    product.refresh_from_db()
    assert result == "expired"
    assert order.status == Order.Status.EXPIRED
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert product.stock_quantity == 2
    assert PaymentAttempt.objects.filter(order=order).exists() is False
    assert gateway.initiations == []


@pytest.mark.django_db(transaction=True)
def test_concurrent_initiation_creates_one_pending_attempt():
    customer = create_customer("initiation-race@example.com")
    category = Category.objects.create(name="Initiation race")
    product = Product.objects.create(
        category=category,
        name="Initiation race product",
        slug="initiation-race-product",
        sku="INITIATION-RACE",
        price=Decimal("25.00"),
        stock_quantity=2,
        status=Product.Status.ACTIVE,
    )
    order = create_order(customer)
    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() + RESERVATION_LIFETIME,
    )
    start_barrier = Barrier(2)
    gateway_barrier = Barrier(2)
    gateway = FakeGateway(initiation_barrier=gateway_barrier)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_initiate_in_thread, order.pk, gateway, start_barrier)
            for _ in range(2)
        ]
        results = [future.result(timeout=10) for future in futures]

    assert results[0][0] == results[1][0]
    assert sorted(created for _, created in results) == [False, True]
    assert (
        PaymentAttempt.objects.filter(
            order=order,
            status=PaymentAttempt.Status.PENDING,
        ).count()
        == 1
    )
    assert len(gateway.initiations) == 2
    assert gateway.initiations[0][3] == gateway.initiations[1][3]
    attempt = PaymentAttempt.objects.get(order=order)
    assert gateway.initiations[0][3] == attempt.idempotency_key
    assert attempt.gateway_reference == f"fake-{attempt.idempotency_key}"


def _verify_in_thread(attempt_id, gateway, barrier):
    close_old_connections()
    try:
        attempt = PaymentAttempt.objects.get(pk=attempt_id)
        barrier.wait()
        result = verify_order_payment(
            attempt=attempt,
            callback_data={"thread": str(uuid4())},
            gateway=gateway,
        )
        return result.status
    finally:
        close_old_connections()


def _verify_after_signal(attempt_id, gateway):
    close_old_connections()
    try:
        attempt = PaymentAttempt.objects.get(pk=attempt_id)
        result = verify_order_payment(
            attempt=attempt,
            callback_data={"race": "product-lock"},
            gateway=gateway,
        )
        return result.status
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_success_waiting_on_product_lock_cannot_finalize_after_expiry():
    customer = create_customer("product-lock-expiry@example.com")
    category = Category.objects.create(name="Product lock expiry")
    product = Product.objects.create(
        category=category,
        name="Product lock expiry product",
        slug="product-lock-expiry-product",
        sku="PRODUCT-LOCK-EXPIRY",
        price=Decimal("25.00"),
        stock_quantity=3,
        status=Product.Status.ACTIVE,
    )
    order = create_order(customer)
    reservation = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() + RESERVATION_LIFETIME,
    )
    gateway = FakeGateway()
    attempt, _, _ = initiate_order_payment(order=order, gateway=gateway)
    InventoryReservation.objects.filter(pk=reservation.pk).update(
        expires_at=timezone.now() + timedelta(seconds=1)
    )
    verified = Event()
    gateway.verification_event = verified

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            Product.objects.select_for_update().get(pk=product.pk)
            future = executor.submit(_verify_after_signal, attempt.pk, gateway)
            assert verified.wait(timeout=5)
            sleep(1.2)
        result = future.result(timeout=10)

    order.refresh_from_db()
    attempt.refresh_from_db()
    reservation.refresh_from_db()
    product.refresh_from_db()
    assert result == PaymentAttempt.Status.FAILED
    assert attempt.status == PaymentAttempt.Status.FAILED
    assert order.status == Order.Status.EXPIRED
    assert reservation.status == InventoryReservation.Status.RELEASED
    assert product.stock_quantity == 3


@pytest.mark.django_db(transaction=True)
def test_concurrent_successful_verification_deducts_stock_exactly_once():
    customer = create_customer("verification-race@example.com")
    category = Category.objects.create(name="Verification race")
    first = Product.objects.create(
        category=category,
        name="First race product",
        slug="first-race-product",
        sku="FIRST-RACE",
        price=Decimal("10.00"),
        stock_quantity=5,
        status=Product.Status.ACTIVE,
    )
    second = Product.objects.create(
        category=category,
        name="Second race product",
        slug="second-race-product",
        sku="SECOND-RACE",
        price=Decimal("5.00"),
        stock_quantity=6,
        status=Product.Status.ACTIVE,
    )
    order = create_order(customer)
    reservations = [
        InventoryReservation.objects.create(
            order=order,
            product=second,
            quantity=1,
            expires_at=timezone.now() + RESERVATION_LIFETIME,
        ),
        InventoryReservation.objects.create(
            order=order,
            product=first,
            quantity=2,
            expires_at=timezone.now() + RESERVATION_LIFETIME,
        ),
    ]
    gateway = FakeGateway()
    attempt, _, _ = initiate_order_payment(order=order, gateway=gateway)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_verify_in_thread, attempt.pk, gateway, barrier)
            for _ in range(2)
        ]
        results = [future.result(timeout=10) for future in futures]

    order.refresh_from_db()
    first.refresh_from_db()
    second.refresh_from_db()
    attempt.refresh_from_db()
    assert results == [PaymentAttempt.Status.SUCCESS] * 2
    assert order.status == Order.Status.PAID
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert first.stock_quantity == 3
    assert second.stock_quantity == 5
    assert all(
        reservation.status == InventoryReservation.Status.CONSUMED
        for reservation in InventoryReservation.objects.filter(
            pk__in=[item.pk for item in reservations]
        )
    )


@pytest.mark.django_db
def test_payment_endpoints_are_documented(api_client):
    response = api_client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    paths = response.json()["paths"]
    initiation = paths["/api/v1/orders/{order_id}/payments/"]["post"]
    verification = paths["/api/v1/orders/{order_id}/payments/{payment_id}/verify/"][
        "post"
    ]
    assert initiation["security"] == [{"jwtAuth": []}]
    assert verification["security"] == [{"jwtAuth": []}]
    assert {"200", "201", "400", "401", "404", "409", "502", "503"} <= (
        initiation["responses"].keys()
    )
    assert {"200", "400", "401", "404", "409", "503"} <= verification[
        "responses"
    ].keys()
