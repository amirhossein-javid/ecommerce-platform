import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.money import STORE_CURRENCY, validate_whole_rial


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payment_attempts",
    )
    status = models.CharField(
        max_length=7,
        choices=Status,
        default=Status.PENDING,
    )
    amount = models.DecimalField(
        max_digits=24,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00")), validate_whole_rial],
    )
    currency = models.CharField(max_length=3, default=STORE_CURRENCY)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    gateway = models.CharField(max_length=50)
    gateway_reference = models.CharField(max_length=255, null=True, blank=True)
    provider_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    pre_checkout_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    payment_url = models.URLField(max_length=2048, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("order",),
                condition=Q(status="PENDING"),
                name="payments_one_pending_order",
            ),
            models.UniqueConstraint(
                fields=("gateway", "gateway_reference"),
                name="payments_gateway_ref_unique",
            ),
            models.UniqueConstraint(
                fields=("gateway", "provider_transaction_id"),
                name="payments_gateway_tx_unique",
            ),
            models.UniqueConstraint(
                fields=("gateway", "pre_checkout_transaction_id"),
                name="payments_gateway_precheckout_unique",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("PENDING", "SUCCESS", "FAILED")),
                name="payments_attempt_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="payments_attempt_amount_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(amount=models.functions.Floor("amount")),
                name="payments_attempt_amount_whole_irr",
            ),
            models.CheckConstraint(
                condition=Q(currency=STORE_CURRENCY),
                name="payments_attempt_currency_irr",
            ),
            models.CheckConstraint(
                condition=~Q(gateway=""),
                name="payments_attempt_gateway_set",
            ),
            models.CheckConstraint(
                condition=Q(gateway_reference__isnull=True) | ~Q(gateway_reference=""),
                name="payments_attempt_ref_set",
            ),
            models.CheckConstraint(
                condition=Q(provider_transaction_id__isnull=True)
                | ~Q(provider_transaction_id=""),
                name="payments_attempt_tx_set",
            ),
            models.CheckConstraint(
                condition=Q(pre_checkout_transaction_id__isnull=True)
                | ~Q(pre_checkout_transaction_id=""),
                name="payments_attempt_precheckout_set",
            ),
            models.CheckConstraint(
                condition=Q(payment_url__isnull=True) | ~Q(payment_url=""),
                name="payments_attempt_url_set",
            ),
        ]
        indexes = [
            models.Index(
                fields=("order", "created_at"),
                name="payments_order_created_idx",
            )
        ]

    def __str__(self):
        return f"Payment attempt {self.pk} for order {self.order_id} ({self.status})"

    @property
    def customer_payment_identifier(self):
        if self.gateway == "bale":
            return self.gateway_reference
        return None


class BaleWebhookUpdate(models.Model):
    class EventType(models.TextChoices):
        PRE_CHECKOUT = "PRE_CHECKOUT", "Pre-checkout"
        SUCCESSFUL_PAYMENT = "SUCCESSFUL_PAYMENT", "Successful payment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        PROCESSED = "PROCESSED", "Processed"
        REJECTED = "REJECTED", "Rejected"

    update_id = models.BigIntegerField(unique=True)
    event_type = models.CharField(max_length=18, choices=EventType)
    status = models.CharField(
        max_length=10,
        choices=Status,
        default=Status.PENDING,
    )
    payment_attempt = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.SET_NULL,
        related_name="bale_webhook_updates",
        null=True,
        blank=True,
    )
    provider_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        max_digits=24,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, null=True, blank=True)
    received_at = models.DateTimeField(default=timezone.now, editable=False)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(event_type__in=("PRE_CHECKOUT", "SUCCESSFUL_PAYMENT")),
                name="payments_bale_update_event_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=("PENDING", "PROCESSING", "PROCESSED", "REJECTED")
                ),
                name="payments_bale_update_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(provider_transaction_id__isnull=True)
                | ~Q(provider_transaction_id=""),
                name="payments_bale_update_tx_set",
            ),
        ]

    def __str__(self):
        return f"Bale update {self.update_id} ({self.event_type})"
