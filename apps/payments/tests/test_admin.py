from decimal import Decimal

import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import Order
from apps.payments.admin import BaleWebhookUpdateAdmin, PaymentAttemptAdmin
from apps.payments.models import BaleWebhookUpdate, PaymentAttempt


def create_attempt():
    customer = CustomerProfile.objects.create(
        user=User.objects.create_user("customer@example.com")
    )
    order = Order.objects.create(
        customer=customer,
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
    return PaymentAttempt.objects.create(
        order=order,
        amount=order.grand_total,
        gateway="bale",
        gateway_reference="private-gateway-reference",
        provider_transaction_id="private-provider-transaction",
        payment_url="https://example.com/private-payment-token",
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
    assert post_response.status_code == 403
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.PENDING
