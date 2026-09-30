from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.products.models import Product

from .models import InventoryReservation, Order

RESERVATION_LIFETIME = timedelta(minutes=15)


class InventoryReservationError(Exception):
    """Base exception for rejected inventory reservation operations."""


class InvalidReservationQuantity(InventoryReservationError):
    pass


class InsufficientAvailableStock(InventoryReservationError):
    def __init__(self, product_id):
        self.product_id = product_id
        super().__init__(f"Insufficient available stock for product {product_id}.")


class ReservationAlreadyExists(InventoryReservationError):
    pass


def calculate_available_stock(*, product, at=None):
    """Return current stock minus active reservations that have not expired."""
    at = at or timezone.now()
    current_stock = Product.objects.values_list("stock_quantity", flat=True).get(
        pk=product.pk
    )
    reserved = InventoryReservation.objects.filter(
        product_id=product.pk,
        status=InventoryReservation.Status.ACTIVE,
        expires_at__gt=at,
    ).aggregate(total=Sum("quantity", default=0))["total"]
    return current_stock - reserved


def create_inventory_reservations(*, order, product_quantities, at=None):
    """Atomically reserve stock for all requested products or none of them."""
    requested = _normalize_product_quantities(product_quantities)
    if not requested:
        return []

    at = at or timezone.now()
    expires_at = at + RESERVATION_LIFETIME

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        locked_products = list(
            Product.objects.select_for_update().filter(pk__in=requested).order_by("pk")
        )
        if len(locked_products) != len(requested):
            raise Product.DoesNotExist("One or more products no longer exist.")

        if InventoryReservation.objects.filter(
            order=locked_order,
            product_id__in=requested,
        ).exists():
            raise ReservationAlreadyExists(
                "The order already has a reservation for a requested product."
            )

        reserved_quantities = dict(
            InventoryReservation.objects.filter(
                product_id__in=requested,
                status=InventoryReservation.Status.ACTIVE,
                expires_at__gt=at,
            )
            .values("product_id")
            .annotate(total=Sum("quantity"))
            .values_list("product_id", "total")
        )

        for product in locked_products:
            available = product.stock_quantity - reserved_quantities.get(product.pk, 0)
            if requested[product.pk] > available:
                raise InsufficientAvailableStock(product.pk)

        return InventoryReservation.objects.bulk_create(
            [
                InventoryReservation(
                    order=locked_order,
                    product=product,
                    quantity=requested[product.pk],
                    expires_at=expires_at,
                )
                for product in locked_products
            ]
        )


def release_inventory_reservation(*, reservation):
    """Release an active reservation, preserving either terminal state."""
    return _transition_active_reservation(
        reservation=reservation,
        target_status=InventoryReservation.Status.RELEASED,
    )


def consume_inventory_reservation(*, reservation):
    """Consume an active reservation, preserving either terminal state."""
    return _transition_active_reservation(
        reservation=reservation,
        target_status=InventoryReservation.Status.CONSUMED,
    )


def _transition_active_reservation(*, reservation, target_status):
    with transaction.atomic():
        locked_reservation = InventoryReservation.objects.select_for_update().get(
            pk=reservation.pk
        )
        if locked_reservation.status != InventoryReservation.Status.ACTIVE:
            return locked_reservation

        locked_reservation.status = target_status
        locked_reservation.save(update_fields=("status", "updated_at"))
        return locked_reservation


def _normalize_product_quantities(product_quantities):
    pairs = (
        product_quantities.items()
        if hasattr(product_quantities, "items")
        else product_quantities
    )
    requested = {}
    for product, quantity in pairs:
        if product.pk is None:
            raise Product.DoesNotExist("Products must be saved before reservation.")
        if quantity <= 0:
            raise InvalidReservationQuantity(
                "Reservation quantity must be greater than zero."
            )
        requested[product.pk] = requested.get(product.pk, 0) + quantity
    return requested
