from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections

from apps.accounts.models import CustomerProfile, User
from apps.carts.models import Cart, CartItem
from apps.carts.services import (
    CartNotActive,
    InsufficientStock,
    InvalidQuantity,
    ProductUnavailable,
    add_product,
    change_item_quantity,
    get_or_create_active_customer_cart,
    remove_item,
)
from apps.products.models import Category, Product


@pytest.fixture
def customer(db):
    user = User.objects.create_user("service-customer@example.com")
    return CustomerProfile.objects.create(user=user)


@pytest.fixture
def category(db):
    return Category.objects.create(name="Available products")


@pytest.fixture
def product(category):
    return Product.objects.create(
        category=category,
        name="Available product",
        sku="AVAILABLE-PRODUCT",
        price=Decimal("25.00"),
        stock_quantity=10,
        status=Product.Status.ACTIVE,
    )


@pytest.mark.django_db
def test_get_or_create_active_customer_cart(customer):
    first, first_created = get_or_create_active_customer_cart(customer=customer)
    second, second_created = get_or_create_active_customer_cart(customer=customer)

    assert first_created is True
    assert second_created is False
    assert second.pk == first.pk


@pytest.mark.django_db
def test_add_new_product(product):
    cart = Cart.objects.create()

    item = add_product(cart=cart, product=product, quantity=2)

    assert item.cart == cart
    assert item.product == product
    assert item.quantity == 2


@pytest.mark.django_db
def test_adding_same_product_increases_quantity(product):
    cart = Cart.objects.create()
    existing = CartItem.objects.create(cart=cart, product=product, quantity=2)

    item = add_product(cart=cart, product=product, quantity=3)

    existing.refresh_from_db()
    assert item.pk == existing.pk
    assert existing.quantity == 5


@pytest.mark.django_db
def test_add_rejects_resulting_quantity_above_current_stock(product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=8)

    with pytest.raises(InsufficientStock):
        add_product(cart=cart, product=product, quantity=3)

    item.refresh_from_db()
    assert item.quantity == 8


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [0, -1])
def test_cart_services_reject_nonpositive_quantity(product, quantity):
    cart = Cart.objects.create()

    with pytest.raises(InvalidQuantity):
        add_product(cart=cart, product=product, quantity=quantity)


@pytest.mark.django_db
@pytest.mark.parametrize("unavailable_reason", ["product", "category"])
def test_new_items_reject_unavailable_products(product, unavailable_reason):
    cart = Cart.objects.create()
    if unavailable_reason == "product":
        product.status = Product.Status.ARCHIVED
        product.save(update_fields=("status",))
    else:
        product.category.is_active = False
        product.category.save(update_fields=("is_active",))

    with pytest.raises(ProductUnavailable):
        add_product(cart=cart, product=product, quantity=1)

    assert cart.items.exists() is False


@pytest.mark.django_db
def test_product_visibility_ignores_inactive_ancestor(product):
    parent = Category.objects.create(name="Inactive parent", is_active=False)
    product.category.parent = parent
    product.category.save(update_fields=("parent",))
    cart = Cart.objects.create()

    item = add_product(cart=cart, product=product, quantity=1)

    assert item.quantity == 1


@pytest.mark.django_db
def test_cart_mutations_do_not_reserve_or_decrement_stock(product):
    cart = Cart.objects.create()
    item = add_product(cart=cart, product=product, quantity=2)
    change_item_quantity(item=item, quantity=4)

    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_existing_item_remains_when_stock_later_decreases(product):
    cart = Cart.objects.create()
    item = add_product(cart=cart, product=product, quantity=5)

    product.stock_quantity = 2
    product.save(update_fields=("stock_quantity",))

    item.refresh_from_db()
    assert item.quantity == 5


@pytest.mark.django_db
@pytest.mark.parametrize("unavailable_reason", ["product", "category"])
def test_existing_item_remains_when_product_becomes_unavailable(
    product,
    unavailable_reason,
):
    cart = Cart.objects.create()
    item = add_product(cart=cart, product=product, quantity=3)

    if unavailable_reason == "product":
        product.status = Product.Status.ARCHIVED
        product.save(update_fields=("status",))
    else:
        product.category.is_active = False
        product.category.save(update_fields=("is_active",))

    item.refresh_from_db()
    assert item.quantity == 3


@pytest.mark.django_db
def test_unavailable_existing_product_cannot_be_added_again(product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=2)
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=("status",))

    with pytest.raises(ProductUnavailable):
        add_product(cart=cart, product=product, quantity=1)

    item.refresh_from_db()
    assert item.quantity == 2


@pytest.mark.django_db
def test_change_item_quantity_uses_current_stock(product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=2)
    product.stock_quantity = 3
    product.save(update_fields=("stock_quantity",))

    with pytest.raises(InsufficientStock):
        change_item_quantity(item=item, quantity=4)

    item.refresh_from_db()
    assert item.quantity == 2


@pytest.mark.django_db
def test_remove_item(product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=1)

    remove_item(item=item)

    assert CartItem.objects.filter(pk=item.pk).exists() is False


@pytest.mark.django_db
def test_converted_cart_cannot_be_modified(product):
    cart = Cart.objects.create(status=Cart.Status.CONVERTED)

    with pytest.raises(CartNotActive):
        add_product(cart=cart, product=product, quantity=1)


def _create_active_cart_in_thread(customer_id, barrier):
    close_old_connections()
    try:
        customer = CustomerProfile.objects.get(pk=customer_id)
        barrier.wait()
        cart, _ = get_or_create_active_customer_cart(customer=customer)
        return cart.pk
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_active_cart_creation_returns_one_cart(customer):
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_create_active_cart_in_thread, customer.pk, barrier)
            for _ in range(2)
        ]
        cart_ids = [future.result(timeout=10) for future in futures]

    assert cart_ids[0] == cart_ids[1]
    assert (
        Cart.objects.filter(customer=customer, status=Cart.Status.ACTIVE).count() == 1
    )


def _add_product_in_thread(cart_id, product_id, barrier):
    close_old_connections()
    try:
        cart = Cart.objects.get(pk=cart_id)
        product = Product.objects.get(pk=product_id)
        barrier.wait()
        return add_product(cart=cart, product=product, quantity=2).pk
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_adds_preserve_both_quantity_increases(product):
    cart = Cart.objects.create()
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_add_product_in_thread, cart.pk, product.pk, barrier)
            for _ in range(2)
        ]
        item_ids = [future.result(timeout=10) for future in futures]

    item = CartItem.objects.get(cart=cart, product=product)
    assert item_ids == [item.pk, item.pk]
    assert item.quantity == 4
    product.refresh_from_db()
    assert product.stock_quantity == 10
