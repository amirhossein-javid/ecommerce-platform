from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import requests
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import InventoryReservation, Order
from apps.orders.services import RESERVATION_LIFETIME
from apps.payments.bale import BaleGateway
from apps.payments.gateways import (
    PaymentGatewayError,
    PaymentGatewayUnavailable,
    TransactionStatus,
)
from apps.payments.models import PaymentAttempt
from apps.products.models import Category, Product

BOT_TOKEN = "123456:test-bot-secret"
PROVIDER_TOKEN = "WALLET-TEST-provider-secret"
IDEMPOTENCY_KEY = UUID("12345678-1234-5678-1234-567812345678")


class StubResponse:
    def __init__(self, *, body=None, status_code=200, json_error=None):
        self.body = body
        self.status_code = status_code
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("upstream response contained sensitive data")

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.body


class StubSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_gateway(session, **overrides):
    values = {
        "bot_token": BOT_TOKEN,
        "provider_token": PROVIDER_TOKEN,
        "connect_timeout": 2.5,
        "read_timeout": 7.5,
        "session": session,
    }
    values.update(overrides)
    return BaleGateway(**values)


def create_payable_order():
    user = User.objects.create_user(f"bale-{uuid4()}@example.com")
    customer = CustomerProfile.objects.create(user=user)
    category = Category.objects.create(name=f"Bale category {uuid4()}")
    product = Product.objects.create(
        category=category,
        name="Bale product",
        slug=f"bale-product-{uuid4()}",
        sku=f"BALE-{uuid4()}",
        price=Decimal("25"),
        stock_quantity=10,
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
    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() + RESERVATION_LIFETIME,
    )
    return order


def test_create_invoice_link_request_and_result_mapping():
    session = StubSession(StubResponse(body={"ok": True, "result": "invoice-123"}))
    gateway = make_gateway(session)

    initiation = gateway.initiate(
        order_id=42,
        amount=Decimal("25000"),
        currency="IRR",
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert initiation.gateway_reference == "invoice-123"
    assert initiation.payment_url is None
    assert session.calls == [
        (
            f"https://tapi.bale.ai/bot{BOT_TOKEN}/createInvoiceLink",
            {
                "json": {
                    "title": "Order payment",
                    "description": "Payment for order 42",
                    "payload": f"pay:{IDEMPOTENCY_KEY.hex}",
                    "provider_token": PROVIDER_TOKEN,
                    "prices": [{"label": "Order total", "amount": 25000}],
                },
                "timeout": (2.5, 7.5),
            },
        )
    ]
    request_body = session.calls[0][1]["json"]
    assert isinstance(request_body["prices"][0]["amount"], int)
    assert 1 <= len(request_body["title"]) <= 32
    assert 1 <= len(request_body["description"]) <= 255
    assert 1 <= len(request_body["payload"].encode()) <= 128
    assert "idempotency_key" not in request_body
    assert "idempotency" not in session.calls[0][1]


def test_invoice_payload_is_stable_for_the_same_payment_attempt():
    session = StubSession(
        StubResponse(body={"ok": True, "result": "invoice-first"}),
        StubResponse(body={"ok": True, "result": "invoice-second"}),
    )
    gateway = make_gateway(session)

    for order_id in (1, 999):
        gateway.initiate(
            order_id=order_id,
            amount=Decimal("25"),
            currency="IRR",
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert (
        session.calls[0][1]["json"]["payload"] == session.calls[1][1]["json"]["payload"]
    )


@pytest.mark.parametrize(
    "response",
    [
        StubResponse(
            body={"ok": False, "description": "provider secret upstream detail"}
        ),
        StubResponse(json_error=ValueError("not JSON")),
        StubResponse(body={"ok": False}, status_code=502),
        StubResponse(body={"ok": True}),
        StubResponse(body={"ok": True, "result": {"unexpected": "object"}}),
    ],
)
def test_create_invoice_link_rejects_gateway_error_responses(response):
    gateway = make_gateway(StubSession(response))

    with pytest.raises(PaymentGatewayError):
        gateway.initiate(
            order_id=1,
            amount=Decimal("25"),
            currency="IRR",
            idempotency_key=IDEMPOTENCY_KEY,
        )


@pytest.mark.parametrize(
    "network_error",
    [requests.Timeout("secret timeout detail"), requests.ConnectionError("secret")],
)
def test_create_invoice_link_maps_network_failures_to_safe_error(network_error):
    gateway = make_gateway(StubSession(network_error))

    with pytest.raises(
        PaymentGatewayUnavailable,
        match=r"^Bale gateway request failed\.$",
    ) as exc_info:
        gateway.initiate(
            order_id=1,
            amount=Decimal("25"),
            currency="IRR",
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert "secret" not in str(exc_info.value)
    assert BOT_TOKEN not in str(exc_info.value)


@pytest.mark.parametrize(
    "provider_status",
    [
        TransactionStatus.PENDING,
        TransactionStatus.PAID,
        TransactionStatus.FAILED,
        TransactionStatus.REJECTED,
    ],
)
def test_inquire_transaction_parses_documented_status_and_integer_amount(
    provider_status,
):
    result = {
        "id": "transaction-123",
        "status": provider_status.value,
        "userID": 987,
        "amount": 25000,
        "createdAt": 1_700_000_000,
    }
    session = StubSession(StubResponse(body={"ok": True, "result": result}))
    gateway = make_gateway(session)

    transaction = gateway.inquire_transaction("transaction-123")

    assert transaction.transaction_id == "transaction-123"
    assert transaction.status == provider_status
    assert transaction.amount == Decimal("25000")
    assert transaction.user_id == 987
    assert transaction.created_at == 1_700_000_000
    assert session.calls == [
        (
            f"https://tapi.bale.ai/bot{BOT_TOKEN}/inquireTransaction",
            {
                "json": {"transaction_id": "transaction-123"},
                "timeout": (2.5, 7.5),
            },
        )
    ]
    assert PROVIDER_TOKEN not in str(session.calls)


@pytest.mark.parametrize(
    "result",
    [
        {
            "id": "transaction-123",
            "status": "unknown",
            "userID": 1,
            "amount": 25,
            "createdAt": 1,
        },
        {
            "id": "transaction-123",
            "status": "paid",
            "userID": 1,
            "amount": "25",
            "createdAt": 1,
        },
    ],
)
def test_inquire_transaction_rejects_malformed_results(result):
    gateway = make_gateway(
        StubSession(StubResponse(body={"ok": True, "result": result}))
    )

    with pytest.raises(PaymentGatewayError):
        gateway.inquire_transaction("transaction-123")


def test_answer_pre_checkout_query_uses_documented_request_shape():
    session = StubSession(
        StubResponse(body={"ok": True, "result": True}),
        StubResponse(body={"ok": True, "result": True}),
    )
    gateway = make_gateway(session)

    gateway.answer_pre_checkout_query(pre_checkout_query_id="tx-1", ok=True)
    gateway.answer_pre_checkout_query(
        pre_checkout_query_id="tx-2",
        ok=False,
        error_message="Payment cannot be completed.",
    )

    assert session.calls == [
        (
            f"https://tapi.bale.ai/bot{BOT_TOKEN}/answerPreCheckoutQuery",
            {
                "json": {"pre_checkout_query_id": "tx-1", "ok": True},
                "timeout": (2.5, 7.5),
            },
        ),
        (
            f"https://tapi.bale.ai/bot{BOT_TOKEN}/answerPreCheckoutQuery",
            {
                "json": {
                    "pre_checkout_query_id": "tx-2",
                    "ok": False,
                    "error_message": "Payment cannot be completed.",
                },
                "timeout": (2.5, 7.5),
            },
        ),
    ]
    assert PROVIDER_TOKEN not in str(session.calls)


def test_set_webhook_uses_documented_request_shape():
    session = StubSession(StubResponse(body={"ok": True, "result": True}))
    gateway = make_gateway(session)

    gateway.set_webhook("https://shop.example/api/v1/payments/bale/webhook/")

    assert session.calls == [
        (
            f"https://tapi.bale.ai/bot{BOT_TOKEN}/setWebhook",
            {
                "json": {"url": "https://shop.example/api/v1/payments/bale/webhook/"},
                "timeout": (2.5, 7.5),
            },
        )
    ]
    assert PROVIDER_TOKEN not in str(session.calls)


@pytest.mark.parametrize(
    "overrides",
    [
        {"bot_token": ""},
        {"provider_token": ""},
    ],
)
def test_create_invoice_link_rejects_missing_configuration(overrides):
    gateway = make_gateway(StubSession(), **overrides)

    with pytest.raises(PaymentGatewayUnavailable, match="not configured"):
        gateway.initiate(
            order_id=1,
            amount=Decimal("25"),
            currency="IRR",
            idempotency_key=IDEMPOTENCY_KEY,
        )


@pytest.mark.parametrize(
    ("amount", "currency"),
    [(Decimal("25.50"), "IRR"), (Decimal("25"), "USD")],
)
def test_create_invoice_link_rejects_non_integer_irr_amount(amount, currency):
    gateway = make_gateway(StubSession())

    with pytest.raises(PaymentGatewayError, match="amount is invalid"):
        gateway.initiate(
            order_id=1,
            amount=amount,
            currency=currency,
            idempotency_key=IDEMPOTENCY_KEY,
        )


def test_bale_gateway_repr_does_not_expose_credentials():
    gateway = make_gateway(StubSession())

    assert repr(gateway) == "<BaleGateway name='bale'>"
    assert BOT_TOKEN not in repr(gateway)
    assert PROVIDER_TOKEN not in repr(gateway)


@pytest.mark.django_db
def test_bale_identifier_is_persisted_without_tokens_or_fabricated_url(monkeypatch):
    order = create_payable_order()
    session = StubSession(StubResponse(body={"ok": True, "result": "invoice-123"}))
    gateway = make_gateway(session)
    monkeypatch.setattr("apps.payments.services.get_payment_gateway", lambda: gateway)
    api_client = APIClient()
    api_client.force_authenticate(user=order.customer.user)

    response = api_client.post(
        reverse("payments:payment-initiate", kwargs={"order_id": order.pk}),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["payment_url"] is None
    assert "gateway_reference" not in response.json()
    attempt = PaymentAttempt.objects.get(pk=response.json()["id"])
    assert attempt.gateway == "bale"
    assert attempt.gateway_reference == "invoice-123"
    assert attempt.payment_url is None
    assert BOT_TOKEN not in str(attempt.__dict__)
    assert PROVIDER_TOKEN not in str(attempt.__dict__)


@pytest.mark.django_db
def test_bale_gateway_error_is_sanitized_by_customer_api(monkeypatch):
    order = create_payable_order()
    sensitive_detail = "merchant token and private upstream response"
    session = StubSession(
        StubResponse(body={"ok": False, "description": sensitive_detail})
    )
    gateway = make_gateway(session)
    monkeypatch.setattr("apps.payments.services.get_payment_gateway", lambda: gateway)
    api_client = APIClient()
    api_client.force_authenticate(user=order.customer.user)

    response = api_client.post(
        reverse("payments:payment-initiate", kwargs={"order_id": order.pk}),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Payment gateway is temporarily unavailable."}
    response_body = response.content.decode()
    assert sensitive_detail not in response_body
    assert BOT_TOKEN not in response_body
    assert PROVIDER_TOKEN not in response_body


@pytest.mark.django_db
def test_bale_timeout_retry_reuses_durable_attempt_and_payload(monkeypatch):
    order = create_payable_order()
    session = StubSession(
        requests.Timeout("ambiguous timeout"),
        StubResponse(body={"ok": True, "result": "invoice-after-timeout"}),
    )
    gateway = make_gateway(session)
    monkeypatch.setattr("apps.payments.services.get_payment_gateway", lambda: gateway)
    api_client = APIClient()
    api_client.force_authenticate(user=order.customer.user)
    url = reverse("payments:payment-initiate", kwargs={"order_id": order.pk})

    first = api_client.post(url, {}, format="json")
    pending = PaymentAttempt.objects.get(order=order)
    second = api_client.post(url, {}, format="json")

    assert first.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert second.status_code == status.HTTP_200_OK
    assert second.json()["id"] == pending.pk
    assert PaymentAttempt.objects.filter(order=order).count() == 1
    assert (
        session.calls[0][1]["json"]["payload"] == session.calls[1][1]["json"]["payload"]
    )
    pending.refresh_from_db()
    assert pending.gateway_reference == "invoice-after-timeout"


def test_bale_event_verification_is_not_enabled_in_this_phase():
    gateway = make_gateway(StubSession())

    with pytest.raises(PaymentGatewayUnavailable, match="not configured"):
        gateway.verify(gateway_reference="transaction-123", callback_data={})
