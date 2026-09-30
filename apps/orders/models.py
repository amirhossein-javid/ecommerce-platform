from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.accounts.models import CustomerProfile
from apps.accounts.validators import (
    validate_e164_phone_number,
    validate_iran_postal_code,
)
from apps.products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
        PAID = "PAID", "Paid"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=15,
        choices=Status,
        default=Status.PENDING_PAYMENT,
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    grand_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_title = models.CharField(max_length=50, blank=True)
    shipping_recipient_first_name = models.CharField(max_length=150)
    shipping_recipient_last_name = models.CharField(max_length=150)
    shipping_recipient_phone_number = models.CharField(
        max_length=16,
        validators=[validate_e164_phone_number],
    )
    shipping_province = models.CharField(max_length=100)
    shipping_city = models.CharField(max_length=100)
    shipping_address = models.TextField(max_length=500)
    shipping_postal_code = models.CharField(
        max_length=10,
        validators=[validate_iran_postal_code],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=(
                        "PENDING_PAYMENT",
                        "PAID",
                        "PROCESSING",
                        "SHIPPED",
                        "DELIVERED",
                        "CANCELLED",
                        "EXPIRED",
                    )
                ),
                name="orders_order_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="orders_order_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(discount_total__gte=0),
                name="orders_order_discount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(shipping_total__gte=0),
                name="orders_order_shipping_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(grand_total__gte=0),
                name="orders_order_grand_total_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(
                    grand_total=F("subtotal")
                    - F("discount_total")
                    + F("shipping_total")
                ),
                name="orders_order_grand_total_consistent",
            ),
        ]
        indexes = [
            models.Index(
                fields=("status", "created_at"),
                name="orders_status_created_idx",
            )
        ]

    def __str__(self):
        return f"Order {self.pk} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name="order_items",
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="orders_item_unit_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="orders_item_quantity_gt_zero",
            ),
            models.CheckConstraint(
                condition=Q(line_total__gte=0),
                name="orders_item_line_total_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(line_total=F("unit_price") * F("quantity")),
                name="orders_item_line_total_consistent",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"
