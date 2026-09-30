from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Address, CustomerProfile
from apps.carts.models import Cart, CartItem
from apps.products.models import Category, Product

from .models import InventoryReservation, Order, OrderItem

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


class CheckoutError(Exception):
    """Base exception for rejected checkout operations."""


class CheckoutCartUnavailable(CheckoutError):
    pass


class CheckoutAddressUnavailable(CheckoutError):
    pass


class CheckoutProductUnavailable(CheckoutError):
    pass


class CheckoutInsufficientStock(CheckoutError):
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

        reservation_time = at or timezone.now()
        _validate_available_stock(
            products=locked_products,
            requested=requested,
            at=reservation_time,
        )
        return _create_reservations_for_locked_products(
            order=locked_order,
            products=locked_products,
            requested=requested,
            at=reservation_time,
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


def checkout_customer_cart(*, customer, address_id=None, at=None):
    """Create an order and reservations from a customer's active cart."""
    with transaction.atomic():
        locked_customer = CustomerProfile.objects.select_for_update().get(
            pk=customer.pk
        )
        cart = (
            Cart.objects.select_for_update()
            .filter(
                customer=locked_customer,
                status=Cart.Status.ACTIVE,
            )
            .first()
        )
        if cart is None:
            raise CheckoutCartUnavailable("An active cart is required.")

        cart_items = list(
            CartItem.objects.select_for_update().filter(cart=cart).order_by("pk")
        )
        if not cart_items:
            raise CheckoutCartUnavailable("The active cart is empty.")

        address_query = Address.objects.select_for_update().filter(
            customer_profile=locked_customer
        )
        if address_id is None:
            address = address_query.filter(is_default=True).first()
        else:
            address = address_query.filter(pk=address_id).first()
        if address is None:
            raise CheckoutAddressUnavailable(
                "A usable customer shipping address is required."
            )

        quantities = {item.product_id: item.quantity for item in cart_items}
        products = list(
            Product.objects.select_for_update().filter(pk__in=quantities).order_by("pk")
        )
        if len(products) != len(quantities):
            raise CheckoutProductUnavailable(
                "The cart contains an unavailable product."
            )

        categories_by_id = {
            category.pk: category
            for category in Category.objects.select_for_update()
            .filter(pk__in={product.category_id for product in products})
            .order_by("pk")
        }

        products_by_id = {}
        for product in products:
            if (
                product.status != Product.Status.ACTIVE
                or not categories_by_id[product.category_id].is_active
            ):
                raise CheckoutProductUnavailable(
                    "The cart contains an unavailable product."
                )
            products_by_id[product.pk] = product

        reservation_time = at or timezone.now()
        try:
            _validate_available_stock(
                products=products,
                requested=quantities,
                at=reservation_time,
            )
        except InsufficientAvailableStock as exc:
            raise CheckoutInsufficientStock(
                "The cart quantity exceeds available stock."
            ) from exc

        line_values = [
            (
                products_by_id[item.product_id],
                item.quantity,
                products_by_id[item.product_id].price * item.quantity,
            )
            for item in cart_items
        ]
        subtotal = sum(
            (line_total for _, _, line_total in line_values),
            start=0,
        )
        order = Order.objects.create(
            customer=locked_customer,
            status=Order.Status.PENDING_PAYMENT,
            subtotal=subtotal,
            discount_total=0,
            shipping_total=0,
            grand_total=subtotal,
            shipping_title=address.title,
            shipping_recipient_first_name=address.recipient_first_name,
            shipping_recipient_last_name=address.recipient_last_name,
            shipping_recipient_phone_number=address.recipient_phone_number,
            shipping_province=address.province,
            shipping_city=address.city,
            shipping_address=address.address,
            shipping_postal_code=address.postal_code,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    sku=product.sku,
                    unit_price=product.price,
                    quantity=quantity,
                    line_total=line_total,
                )
                for product, quantity, line_total in line_values
            ]
        )
        _create_reservations_for_locked_products(
            order=order,
            products=products,
            requested=quantities,
            at=reservation_time,
        )

        cart.status = Cart.Status.CONVERTED
        cart.save(update_fields=("status", "updated_at"))
        return order


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


def _validate_available_stock(*, products, requested, at):
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
    for product in products:
        available = product.stock_quantity - reserved_quantities.get(product.pk, 0)
        if requested[product.pk] > available:
            raise InsufficientAvailableStock(product.pk)


def _create_reservations_for_locked_products(*, order, products, requested, at):
    expires_at = at + RESERVATION_LIFETIME
    return InventoryReservation.objects.bulk_create(
        [
            InventoryReservation(
                order=order,
                product=product,
                quantity=requested[product.pk],
                expires_at=expires_at,
            )
            for product in products
        ]
    )


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
