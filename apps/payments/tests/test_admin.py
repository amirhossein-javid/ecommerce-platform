from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib import admin
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import InventoryReservation, Order
from apps.payments.admin import BaleWebhookUpdateAdmin, PaymentAttemptAdmin
from apps.payments.bale_webhooks import PROCESSING_LEASE
from apps.payments.models import BaleWebhookUpdate, PaymentAttempt
from apps.products.models import Category, Product


def create_attempt(
    *,
    order_status=Order.Status.PENDING_PAYMENT,
    attempt_status=PaymentAttempt.Status.PENDING,
    refund_status=Order.RefundStatus.NOT_REQUIRED,
):
    customer = CustomerProfile.objects.create(
        user=User.objects.create_user(
            f"customer-{CustomerProfile.objects.count()}@example.com"
        )
    )
    order = Order.objects.create(
        customer=customer,
        status=order_status,
        refund_status=refund_status,
        subtotal=Decimal("100"),
        grand_total=Decimal("100"),
        shipping_recipient_first_name="Customer",
        shipping_recipient_last_name="Name",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Address",
        shipping_postal_code="1234567890",
    )
    suffix = PaymentAttempt.objects.count()
    return PaymentAttempt.objects.create(
        order=order,
        amount=order.grand_total,
        status=attempt_status,
        gateway="bale",
        gateway_reference=f"private-gateway-reference-{suffix}",
        provider_transaction_id=f"private-provider-transaction-{suffix}",
        payment_url=f"https://example.com/private-payment-token-{suffix}",
    )


def test_payment_models_use_readonly_custom_admins():
    assert isinstance(admin.site._registry[PaymentAttempt], PaymentAttemptAdmin)
    assert isinstance(admin.site._registry[BaleWebhookUpdate], BaleWebhookUpdateAdmin)


@pytest.mark.django_db
def test_payment_admin_hides_private_fields_and_rejects_mutation(client):
    operator = User.objects.create_superuser("admin@example.com", "password")
    attempt = create_attempt()
    client.force_login(operator)
    url = reverse("admin:payments_paymentattempt_change", args=(attempt.pk,))

    get_response = client.get(url)
    filtered_list_response = client.get(
        reverse("admin:payments_paymentattempt_changelist"),
        {"order__id__exact": attempt.order_id},
    )
    post_response = client.post(
        url,
        {"status": PaymentAttempt.Status.SUCCESS, "_save": "Save"},
    )

    assert get_response.status_code == 200
    assert filtered_list_response.status_code == 200
    assert list(filtered_list_response.context_data["cl"].queryset) == [attempt]
    assert b"private-gateway-reference" not in get_response.content
    assert b"private-provider-transaction" not in get_response.content
    assert b"private-payment-token" not in get_response.content
    assert str(attempt.idempotency_key).encode() not in get_response.content
    assert b"private-gateway-reference" not in filtered_list_response.content
    assert b"private-provider-transaction" not in filtered_list_response.content
    assert b"private-payment-token" not in filtered_list_response.content
    assert str(attempt.idempotency_key).encode() not in filtered_list_response.content
    assert post_response.status_code == 403
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.PENDING


@pytest.mark.django_db
def test_payment_operational_filters_surface_domain_attention_states(
    client,
    monkeypatch,
):
    operator = User.objects.create_superuser("admin@example.com", "password")
    retryable = create_attempt(attempt_status=PaymentAttempt.Status.FAILED)
    refund = create_attempt(
        order_status=Order.Status.CANCELLED,
        attempt_status=PaymentAttempt.Status.SUCCESS,
        refund_status=Order.RefundStatus.REQUIRED,
    )
    inconsistent_pending = create_attempt(order_status=Order.Status.PAID)
    inconsistent_success = create_attempt(
        order_status=Order.Status.EXPIRED,
        attempt_status=PaymentAttempt.Status.SUCCESS,
    )
    inconsistent_cancelled = create_attempt(
        order_status=Order.Status.CANCELLED,
        attempt_status=PaymentAttempt.Status.SUCCESS,
    )
    historical_failure = create_attempt(
        order_status=Order.Status.CANCELLED,
        attempt_status=PaymentAttempt.Status.FAILED,
    )
    category = Category.objects.create(name="Operations")
    product = Product.objects.create(
        category=category,
        name="Product",
        sku="PAYMENT-OPS",
        price=Decimal("100"),
        stock_quantity=10,
    )
    current_time = timezone.now()
    elapsed = create_attempt()
    InventoryReservation.objects.create(
        order=elapsed.order,
        product=product,
        quantity=1,
        expires_at=current_time + timedelta(minutes=1),
    )
    invalid_inventory = create_attempt()
    InventoryReservation.objects.create(
        order=invalid_inventory.order,
        product=product,
        quantity=1,
        status=InventoryReservation.Status.RELEASED,
        expires_at=current_time + timedelta(minutes=15),
    )
    monkeypatch.setattr(
        "apps.payments.admin.timezone.now",
        lambda: current_time + timedelta(minutes=2),
    )
    client.force_login(operator)
    url = reverse("admin:payments_paymentattempt_changelist")

    expected_by_filter = {
        "failed_pending": {retryable.pk},
        "payment_elapsed": {elapsed.pk},
        "payment_inventory": {invalid_inventory.pk},
        "refund_required": {refund.pk},
        "inconsistent": {
            inconsistent_pending.pk,
            inconsistent_success.pk,
            inconsistent_cancelled.pk,
        },
    }
    for filter_value, expected_ids in expected_by_filter.items():
        response = client.get(url, {"payment_state": filter_value})
        assert response.status_code == 200
        actual_ids = set(
            response.context_data["cl"].queryset.values_list("pk", flat=True)
        )
        assert actual_ids == expected_ids

    assert historical_failure.pk not in expected_by_filter["failed_pending"]


@pytest.mark.django_db
def test_bale_webhook_filter_uses_authoritative_recovery_lease(client):
    operator = User.objects.create_superuser("admin@example.com", "password")
    now = timezone.now()
    pending = BaleWebhookUpdate.objects.create(
        update_id=1,
        event_type=BaleWebhookUpdate.EventType.SUCCESSFUL_PAYMENT,
    )
    stale = BaleWebhookUpdate.objects.create(
        update_id=2,
        event_type=BaleWebhookUpdate.EventType.SUCCESSFUL_PAYMENT,
        status=BaleWebhookUpdate.Status.PROCESSING,
        processing_started_at=now - PROCESSING_LEASE - timedelta(seconds=1),
    )
    processing = BaleWebhookUpdate.objects.create(
        update_id=3,
        event_type=BaleWebhookUpdate.EventType.SUCCESSFUL_PAYMENT,
        status=BaleWebhookUpdate.Status.PROCESSING,
        processing_started_at=now,
    )
    rejected = BaleWebhookUpdate.objects.create(
        update_id=4,
        event_type=BaleWebhookUpdate.EventType.SUCCESSFUL_PAYMENT,
        status=BaleWebhookUpdate.Status.REJECTED,
    )
    invalid_processing = BaleWebhookUpdate.objects.create(
        update_id=5,
        event_type=BaleWebhookUpdate.EventType.SUCCESSFUL_PAYMENT,
        status=BaleWebhookUpdate.Status.PROCESSING,
    )
    client.force_login(operator)
    url = reverse("admin:payments_balewebhookupdate_changelist")

    expected_by_filter = {
        "recoverable": {pending.pk, stale.pk},
        "processing": {processing.pk},
        "rejected": {rejected.pk},
        "invalid_processing": {invalid_processing.pk},
    }
    for filter_value, expected_ids in expected_by_filter.items():
        response = client.get(url, {"webhook_state": filter_value})
        assert response.status_code == 200
        actual_ids = set(
            response.context_data["cl"].queryset.values_list("pk", flat=True)
        )
        assert actual_ids == expected_ids


@pytest.mark.django_db
def test_payment_operational_columns_do_not_add_per_row_queries(
    django_assert_num_queries,
):
    operator = User.objects.create_superuser("admin@example.com", "password")
    attempts = [
        create_attempt(attempt_status=PaymentAttempt.Status.FAILED) for _ in range(4)
    ]
    request = RequestFactory().get(reverse("admin:payments_paymentattempt_changelist"))
    request.user = operator
    payment_admin = admin.site._registry[PaymentAttempt]
    changelist = payment_admin.get_changelist_instance(request)
    queryset = changelist.get_queryset(request).filter(
        pk__in=[attempt.pk for attempt in attempts]
    )

    with django_assert_num_queries(1):
        rows = list(queryset)
        assert [payment_admin.operational_state(row) for row in rows] == [
            "Failed while order pending"
        ] * 4
        for row in rows:
            payment_admin.customer_email(row)
