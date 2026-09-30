import uuid
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.accounts.models import CustomerProfile, User
from apps.carts.models import Cart, CartItem
from apps.products.models import Category, Product


@pytest.fixture
def customer(db):
    user = User.objects.create_user("cart-customer@example.com")
    return CustomerProfile.objects.create(user=user)


@pytest.fixture
def product(db):
    category = Category.objects.create(name="Cart products")
    return Product.objects.create(
        category=category,
        name="Cart product",
        sku="CART-PRODUCT",
        price=Decimal("10.00"),
        stock_quantity=10,
        status=Product.Status.ACTIVE,
    )


@pytest.mark.django_db
def test_guest_cart_is_valid_and_has_opaque_token():
    cart = Cart()

    cart.full_clean()
    cart.save()

    assert cart.customer is None
    assert cart.status == Cart.Status.ACTIVE
    assert isinstance(cart.token, uuid.UUID)


@pytest.mark.django_db
def test_customer_cart_can_be_created(customer):
    cart = Cart.objects.create(customer=customer)

    assert cart.customer == customer
    assert list(customer.carts.all()) == [cart]


@pytest.mark.django_db
def test_database_rejects_second_active_cart_for_customer(customer):
    Cart.objects.create(customer=customer)

    with pytest.raises(IntegrityError), transaction.atomic():
        Cart.objects.create(customer=customer)


@pytest.mark.django_db
def test_customer_can_have_multiple_converted_carts(customer):
    Cart.objects.create(customer=customer, status=Cart.Status.CONVERTED)
    Cart.objects.create(customer=customer, status=Cart.Status.CONVERTED)

    assert customer.carts.filter(status=Cart.Status.CONVERTED).count() == 2


@pytest.mark.django_db
def test_guest_carts_are_not_limited_by_customer_constraint():
    Cart.objects.create()
    Cart.objects.create()

    assert Cart.objects.filter(customer=None, status=Cart.Status.ACTIVE).count() == 2


@pytest.mark.django_db
def test_cart_item_product_is_unique_within_cart(product):
    cart = Cart.objects.create()
    CartItem.objects.create(cart=cart, product=product, quantity=1)

    with pytest.raises(IntegrityError), transaction.atomic():
        CartItem.objects.create(cart=cart, product=product, quantity=2)


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [0, -1])
def test_database_rejects_nonpositive_cart_item_quantity(product, quantity):
    cart = Cart.objects.create()

    with pytest.raises(IntegrityError), transaction.atomic():
        CartItem.objects.create(cart=cart, product=product, quantity=quantity)


@pytest.mark.django_db
def test_product_deletion_is_protected_while_cart_item_exists(product):
    cart = Cart.objects.create()
    item = CartItem.objects.create(cart=cart, product=product, quantity=1)

    with pytest.raises(ProtectedError):
        product.delete()

    assert CartItem.objects.filter(pk=item.pk).exists()
