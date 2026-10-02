from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models import Sum
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import InventoryReservation, Order
from apps.orders.services import (
    RESERVATION_LIFETIME,
    InsufficientAvailableStock,
    InvalidReservationQuantity,
    ReservationAlreadyExists,
    calculate_available_stock,
    consume_inventory_reservation,
    create_inventory_reservations,
    release_inventory_reservation,
)
from apps.products.models import Category, Product


@pytest.fixture
def customer(db):
    user = User.objects.create_user("reservation-customer@example.com")
    return CustomerProfile.objects.create(user=user)


@pytest.fixture
def order(customer):
    return create_order(customer)


@pytest.fixture
def category(db):
    return Category.objects.create(name="Reservation products")


@pytest.fixture
def product(category):
    return create_product(category, "reserved-product", stock_quantity=10)


def create_order(customer):
    return Order.objects.create(
        customer=customer,
        subtotal=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        shipping_total=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        shipping_title="Home",
        shipping_recipient_first_name="علی",
        shipping_recipient_last_name="احمدی",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="تهران",
        shipping_city="تهران",
        shipping_address="خیابان آزادی، پلاک ۲",
        shipping_postal_code="1234567890",
    )


def create_product(category, slug, *, stock_quantity):
    return Product.objects.create(
        category=category,
        name=slug.replace("-", " ").title(),
        slug=slug,
        sku=slug.upper(),
        price=Decimal("10.00"),
        stock_quantity=stock_quantity,
        status=Product.Status.ACTIVE,
    )


def create_reservation(order, product, **overrides):
    values = {
        "order": order,
        "product": product,
        "quantity": 2,
        "expires_at": timezone.now() + RESERVATION_LIFETIME,
    }
    values.update(overrides)
    return InventoryReservation.objects.create(**values)


@pytest.mark.django_db
def test_reservation_defaults_and_string_representation(order, product):
    reservation = create_reservation(order, product)

    assert reservation.status == InventoryReservation.Status.ACTIVE
    assert reservation.created_at is not None
    assert reservation.updated_at is not None
    assert str(reservation) == f"2 reserved for order {order.pk}"


@pytest.mark.django_db
def test_database_allows_only_one_reservation_per_order_product(order, product):
    create_reservation(order, product)

    with pytest.raises(IntegrityError), transaction.atomic():
        create_reservation(order, product)


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [0, -1])
def test_database_rejects_nonpositive_reservation_quantity(
    order,
    product,
    quantity,
):
    with pytest.raises(IntegrityError), transaction.atomic():
        create_reservation(order, product, quantity=quantity)


@pytest.mark.django_db
def test_database_rejects_unknown_reservation_status(order, product):
    with pytest.raises(IntegrityError), transaction.atomic():
        create_reservation(order, product, status="UNKNOWN")


@pytest.mark.django_db
def test_database_requires_expiry_after_creation(order, product):
    with pytest.raises(IntegrityError), transaction.atomic():
        create_reservation(
            order,
            product,
            expires_at=timezone.now() - RESERVATION_LIFETIME,
        )


@pytest.mark.django_db
def test_product_deletion_is_protected_by_reservation(order, product):
    reservation = create_reservation(order, product)

    with pytest.raises(ProtectedError):
        product.delete()

    assert InventoryReservation.objects.filter(pk=reservation.pk).exists()


@pytest.mark.django_db
def test_order_deletion_cascades_to_reservations(order, product):
    reservation = create_reservation(order, product)

    order.delete()

    assert InventoryReservation.objects.filter(pk=reservation.pk).exists() is False


@pytest.mark.django_db
def test_available_stock_counts_only_active_nonexpired_reservations(
    customer,
    category,
    product,
):
    now = timezone.now()
    create_reservation(
        create_order(customer),
        product,
        quantity=2,
        expires_at=now + RESERVATION_LIFETIME,
    )
    create_reservation(
        create_order(customer),
        product,
        quantity=3,
        status=InventoryReservation.Status.CONSUMED,
        expires_at=now + RESERVATION_LIFETIME,
    )
    create_reservation(
        create_order(customer),
        product,
        quantity=4,
        status=InventoryReservation.Status.RELEASED,
        expires_at=now + RESERVATION_LIFETIME,
    )
    expired = create_reservation(
        create_order(customer),
        product,
        quantity=5,
    )
    InventoryReservation.objects.filter(pk=expired.pk).update(
        created_at=now - RESERVATION_LIFETIME,
        expires_at=now,
    )

    assert calculate_available_stock(product=product, at=now) == 8


@pytest.mark.django_db
def test_create_reservations_uses_fifteen_minute_lifetime_and_preserves_stock(
    order,
    product,
):
    now = timezone.now()

    reservations = create_inventory_reservations(
        order=order,
        product_quantities=[(product, 3)],
        at=now,
    )

    assert len(reservations) == 1
    assert reservations[0].quantity == 3
    assert reservations[0].status == InventoryReservation.Status.ACTIVE
    assert reservations[0].expires_at == now + RESERVATION_LIFETIME
    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_create_reservations_rejects_invalid_quantity(order, product):
    with pytest.raises(InvalidReservationQuantity):
        create_inventory_reservations(
            order=order,
            product_quantities=[(product, 0)],
        )

    assert InventoryReservation.objects.exists() is False


@pytest.mark.django_db
def test_insufficient_stock_rolls_back_all_products(order, category):
    available = create_product(category, "available", stock_quantity=5)
    insufficient = create_product(category, "insufficient", stock_quantity=1)

    with pytest.raises(InsufficientAvailableStock):
        create_inventory_reservations(
            order=order,
            product_quantities=[(available, 2), (insufficient, 2)],
        )

    assert InventoryReservation.objects.filter(order=order).exists() is False
    available.refresh_from_db()
    insufficient.refresh_from_db()
    assert available.stock_quantity == 5
    assert insufficient.stock_quantity == 1


@pytest.mark.django_db
def test_existing_reservation_is_not_replaced(order, product):
    existing = create_reservation(
        order,
        product,
        status=InventoryReservation.Status.RELEASED,
    )

    with pytest.raises(ReservationAlreadyExists):
        create_inventory_reservations(
            order=order,
            product_quantities=[(product, 1)],
        )

    existing.refresh_from_db()
    assert existing.status == InventoryReservation.Status.RELEASED
    assert (
        InventoryReservation.objects.filter(order=order, product=product).count() == 1
    )


@pytest.mark.django_db
def test_release_is_idempotent_and_does_not_change_stock(order, product):
    reservation = create_reservation(order, product)

    released = release_inventory_reservation(reservation=reservation)
    released_again = release_inventory_reservation(reservation=released)

    assert released.status == InventoryReservation.Status.RELEASED
    assert released_again.status == InventoryReservation.Status.RELEASED
    product.refresh_from_db()
    assert product.stock_quantity == 10
    assert calculate_available_stock(product=product) == 10


@pytest.mark.django_db
def test_consume_is_idempotent_and_does_not_change_stock(order, product):
    reservation = create_reservation(order, product)

    consumed = consume_inventory_reservation(reservation=reservation)
    consumed_again = consume_inventory_reservation(reservation=consumed)

    assert consumed.status == InventoryReservation.Status.CONSUMED
    assert consumed_again.status == InventoryReservation.Status.CONSUMED
    product.refresh_from_db()
    assert product.stock_quantity == 10
    assert calculate_available_stock(product=product) == 10


@pytest.mark.django_db
def test_terminal_reservation_states_are_preserved(customer, category, product):
    released = create_reservation(
        create_order(customer),
        product,
        status=InventoryReservation.Status.RELEASED,
    )
    consumed = create_reservation(
        create_order(customer),
        product,
        status=InventoryReservation.Status.CONSUMED,
    )

    consume_result = consume_inventory_reservation(reservation=released)
    release_result = release_inventory_reservation(reservation=consumed)

    assert consume_result.status == InventoryReservation.Status.RELEASED
    assert release_result.status == InventoryReservation.Status.CONSUMED


def _reserve_in_thread(order_id, product_ids, quantities, barrier):
    close_old_connections()
    try:
        order = Order.objects.get(pk=order_id)
        products = {
            product.pk: product
            for product in Product.objects.filter(pk__in=product_ids)
        }
        barrier.wait()
        try:
            create_inventory_reservations(
                order=order,
                product_quantities=[
                    (products[product_id], quantity)
                    for product_id, quantity in zip(
                        product_ids,
                        quantities,
                        strict=True,
                    )
                ],
            )
        except InsufficientAvailableStock:
            return "insufficient"
        return "reserved"
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_competing_reservations_cannot_oversell_product():
    user = User.objects.create_user("reservation-race@example.com")
    customer = CustomerProfile.objects.create(user=user)
    category = Category.objects.create(name="Reservation race")
    product = create_product(category, "race-product", stock_quantity=5)
    orders = [create_order(customer), create_order(customer)]
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _reserve_in_thread,
                order.pk,
                [product.pk],
                [4],
                barrier,
            )
            for order in orders
        ]
        results = [future.result(timeout=10) for future in futures]

    reserved = InventoryReservation.objects.filter(
        product=product,
        status=InventoryReservation.Status.ACTIVE,
    ).aggregate(total=Sum("quantity", default=0))["total"]
    assert sorted(results) == ["insufficient", "reserved"]
    assert reserved == 4
    product.refresh_from_db()
    assert product.stock_quantity == 5


@pytest.mark.django_db(transaction=True)
def test_multi_product_reservations_lock_products_in_deterministic_order():
    user = User.objects.create_user("reservation-ordering@example.com")
    customer = CustomerProfile.objects.create(user=user)
    category = Category.objects.create(name="Reservation ordering")
    first = create_product(category, "first-lock", stock_quantity=5)
    second = create_product(category, "second-lock", stock_quantity=5)
    orders = [create_order(customer), create_order(customer)]
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            _reserve_in_thread,
            orders[0].pk,
            [first.pk, second.pk],
            [3, 3],
            barrier,
        )
        second_future = executor.submit(
            _reserve_in_thread,
            orders[1].pk,
            [second.pk, first.pk],
            [3, 3],
            barrier,
        )
        results = [
            first_future.result(timeout=10),
            second_future.result(timeout=10),
        ]

    assert sorted(results) == ["insufficient", "reserved"]
    for product in (first, second):
        reserved = InventoryReservation.objects.filter(
            product=product,
            status=InventoryReservation.Status.ACTIVE,
        ).aggregate(total=Sum("quantity", default=0))["total"]
        assert reserved == 3
