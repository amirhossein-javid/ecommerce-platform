import uuid

from django.db import transaction

from apps.accounts.models import CustomerProfile
from apps.products.models import Product

from .models import Cart, CartItem


class CartError(Exception):
    """Base exception for rejected cart mutations."""


class InvalidQuantity(CartError):
    pass


class InsufficientStock(CartError):
    pass


class ProductUnavailable(CartError):
    pass


class CartNotActive(CartError):
    pass


class GuestCartNotFound(CartError):
    pass


def get_or_create_active_customer_cart(*, customer):
    """Return a customer's active cart, serializing competing creation attempts."""
    with transaction.atomic():
        locked_customer = CustomerProfile.objects.select_for_update().get(
            pk=customer.pk
        )
        cart = Cart.objects.filter(
            customer=locked_customer,
            status=Cart.Status.ACTIVE,
        ).first()
        if cart is not None:
            return cart, False
        return Cart.objects.create(customer=locked_customer), True


def add_product(*, cart, product, quantity):
    """Add quantity to a product, or create a new item when it is purchasable."""
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        locked_cart = _get_locked_active_cart(cart.pk)
        locked_product = (
            Product.objects.select_for_update()
            .select_related("category")
            .get(pk=product.pk)
        )
        item = (
            CartItem.objects.select_for_update()
            .filter(cart=locked_cart, product=locked_product)
            .first()
        )

        if not _is_purchasable(locked_product):
            raise ProductUnavailable("Product is not currently purchasable.")

        if item is None:
            resulting_quantity = quantity
        else:
            resulting_quantity = item.quantity + quantity

        _validate_stock(locked_product, resulting_quantity)

        if item is None:
            return CartItem.objects.create(
                cart=locked_cart,
                product=locked_product,
                quantity=resulting_quantity,
            )

        item.quantity = resulting_quantity
        item.save(update_fields=("quantity", "updated_at"))
        return item


def change_item_quantity(*, item, quantity):
    """Set an existing item's quantity without revalidating later availability."""
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        locked_cart = _get_locked_active_cart(item.cart_id)
        locked_product = Product.objects.select_for_update().get(pk=item.product_id)
        locked_item = CartItem.objects.select_for_update().get(
            pk=item.pk,
            cart=locked_cart,
            product=locked_product,
        )
        _validate_stock(locked_product, quantity)
        locked_item.quantity = quantity
        locked_item.save(update_fields=("quantity", "updated_at"))
        return locked_item


def remove_item(*, item):
    """Remove an item from an active cart."""
    with transaction.atomic():
        locked_cart = _get_locked_active_cart(item.cart_id)
        locked_item = CartItem.objects.select_for_update().get(
            pk=item.pk,
            cart=locked_cart,
        )
        locked_item.delete()


def merge_guest_cart(*, customer, guest_token):
    """Atomically consume a guest cart into a customer's active cart."""
    with transaction.atomic():
        locked_customer = CustomerProfile.objects.select_for_update().get(
            pk=customer.pk
        )
        try:
            guest_cart = Cart.objects.select_for_update().get(
                token=guest_token,
                customer__isnull=True,
                status=Cart.Status.ACTIVE,
            )
        except Cart.DoesNotExist as exc:
            raise GuestCartNotFound("Guest cart not found.") from exc

        customer_cart = (
            Cart.objects.select_for_update()
            .filter(
                customer=locked_customer,
                status=Cart.Status.ACTIVE,
            )
            .first()
        )
        if customer_cart is None:
            guest_cart.customer = locked_customer
            guest_cart.token = uuid.uuid4()
            guest_cart.save(update_fields=("customer", "token", "updated_at"))
            return guest_cart

        guest_items = list(
            CartItem.objects.select_for_update().filter(cart=guest_cart).order_by("pk")
        )
        customer_items = {
            item.product_id: item
            for item in CartItem.objects.select_for_update()
            .filter(cart=customer_cart)
            .order_by("pk")
        }

        for guest_item in guest_items:
            customer_item = customer_items.get(guest_item.product_id)
            if customer_item is None:
                guest_item.cart = customer_cart
                guest_item.save(update_fields=("cart",))
                customer_items[guest_item.product_id] = guest_item
                continue

            customer_item.quantity += guest_item.quantity
            customer_item.save(update_fields=("quantity", "updated_at"))
            guest_item.delete()

        guest_cart.delete()
        return customer_cart


def _get_locked_active_cart(cart_id):
    cart = Cart.objects.select_for_update().get(pk=cart_id)
    if cart.status != Cart.Status.ACTIVE:
        raise CartNotActive("Converted carts cannot be modified.")
    return cart


def _validate_positive_quantity(quantity):
    if quantity <= 0:
        raise InvalidQuantity("Quantity must be greater than zero.")


def _validate_stock(product, quantity):
    if quantity > product.stock_quantity:
        raise InsufficientStock("Requested quantity exceeds current stock.")


def _is_purchasable(product):
    return product.status == Product.Status.ACTIVE and product.category.is_active
