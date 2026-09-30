import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

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
