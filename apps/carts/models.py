import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.accounts.models import CustomerProfile
from apps.products.models import Product


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CONVERTED = "CONVERTED", "Converted"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        related_name="carts",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=9,
        choices=Status,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("customer",),
                condition=Q(status="ACTIVE"),
                name="carts_unique_active_cart_per_customer",
            )
        ]

    def __str__(self):
        return f"Cart {self.pk} ({self.status})"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("cart", "product"),
                name="carts_unique_product_per_cart",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="carts_cart_item_quantity_gt_zero",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product}"
