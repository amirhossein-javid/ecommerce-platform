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

        if item is None:
            if not _is_purchasable(locked_product):
                raise ProductUnavailable("Product is not currently purchasable.")
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
