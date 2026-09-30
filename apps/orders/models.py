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
        max_digits=24,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_total = models.DecimalField(
        max_digits=24,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_total = models.DecimalField(
        max_digits=24,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    grand_total = models.DecimalField(
        max_digits=24,
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
        max_digits=22,
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


class InventoryReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CONSUMED = "CONSUMED", "Consumed"
        RELEASED = "RELEASED", "Released"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="inventory_reservations",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="inventory_reservations",
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(
        max_length=8,
        choices=Status,
        default=Status.ACTIVE,
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("order", "product"),
                name="orders_unique_reservation_per_product",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="orders_reservation_quantity_gt_zero",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("ACTIVE", "CONSUMED", "RELEASED")),
                name="orders_reservation_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("created_at")),
                name="orders_reservation_expiry_after_creation",
            ),
        ]
        indexes = [
            models.Index(
                fields=("product", "expires_at"),
                condition=Q(status="ACTIVE"),
                name="orders_active_reservation_idx",
            )
        ]

    def __str__(self):
        return f"{self.quantity} reserved for order {self.order_id}"
