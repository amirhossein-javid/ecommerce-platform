from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.accounts.models import Address, CustomerProfile, User
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product


@pytest.fixture
def customer(db):
    user = User.objects.create_user("order-customer@example.com")
    return CustomerProfile.objects.create(user=user)


@pytest.fixture
def address(customer):
    return Address.objects.create(
        customer_profile=customer,
        title="Home",
        recipient_first_name="علی",
        recipient_last_name="احمدی",
        recipient_phone_number="+989121234567",
        province="تهران",
        city="تهران",
        address="خیابان آزادی، کوچه یک، پلاک ۲",
        postal_code="1234567890",
        is_default=True,
    )


@pytest.fixture
def product(db):
    category = Category.objects.create(name="Order products")
    return Product.objects.create(
        category=category,
        name="Historical product",
        sku="HISTORICAL-SKU",
        price=Decimal("25.00"),
        stock_quantity=5,
        status=Product.Status.ACTIVE,
    )


def build_order(customer, address, **overrides):
    values = {
        "customer": customer,
        "subtotal": Decimal("100.00"),
        "discount_total": Decimal("10.00"),
        "shipping_total": Decimal("5.00"),
        "grand_total": Decimal("95.00"),
        "shipping_title": address.title,
        "shipping_recipient_first_name": address.recipient_first_name,
        "shipping_recipient_last_name": address.recipient_last_name,
        "shipping_recipient_phone_number": address.recipient_phone_number,
        "shipping_province": address.province,
        "shipping_city": address.city,
        "shipping_address": address.address,
        "shipping_postal_code": address.postal_code,
    }
    values.update(overrides)
    return Order(**values)


@pytest.mark.django_db
def test_order_defaults_to_pending_payment_and_has_timestamps(customer, address):
    order = build_order(customer, address)

    order.full_clean()
    order.save()

    assert order.status == Order.Status.PENDING_PAYMENT
    assert order.created_at is not None
    assert order.updated_at is not None
    assert str(order) == f"Order {order.pk} ({Order.Status.PENDING_PAYMENT})"


@pytest.mark.django_db
@pytest.mark.parametrize("order_status", list(Order.Status.values))
def test_all_order_statuses_are_valid(customer, address, order_status):
    order = build_order(customer, address, status=order_status)

    order.full_clean()

    assert order.status == order_status


@pytest.mark.django_db
def test_database_rejects_unknown_order_status(customer, address):
    order = build_order(customer, address, status="UNKNOWN")

    with pytest.raises(IntegrityError), transaction.atomic():
        order.save()


@pytest.mark.django_db
def test_shipping_address_is_an_independent_snapshot(customer, address):
    order = build_order(customer, address)
    order.save()

    address.recipient_first_name = "رضا"
    address.city = "کرج"
    address.address = "نشانی جدید"
    address.save()
    address.delete()
    order.refresh_from_db()

    assert order.shipping_recipient_first_name == "علی"
    assert order.shipping_city == "تهران"
    assert order.shipping_address == "خیابان آزادی، کوچه یک، پلاک ۲"


@pytest.mark.django_db
def test_customer_deletion_is_protected_when_orders_exist(customer, address):
    order = build_order(customer, address)
    order.save()

    with pytest.raises(ProtectedError):
        customer.delete()

    assert Order.objects.filter(pk=order.pk).exists()


@pytest.mark.django_db
def test_order_timestamp_updates_without_changing_creation_time(customer, address):
    order = build_order(customer, address)
    order.save()
    original_created_at = order.created_at
    stale_updated_at = timezone.now() - timedelta(days=1)
    Order.objects.filter(pk=order.pk).update(updated_at=stale_updated_at)

    order.status = Order.Status.PAID
    order.save(update_fields=("status", "updated_at"))
    order.refresh_from_db()

    assert order.created_at == original_created_at
    assert order.updated_at > stale_updated_at


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subtotal", Decimal("-1.00")),
        ("discount_total", Decimal("-1.00")),
        ("shipping_total", Decimal("-1.00")),
        ("grand_total", Decimal("-1.00")),
    ],
)
def test_negative_order_money_fails_model_validation(
    customer,
    address,
    field,
    value,
):
    order = build_order(customer, address, **{field: value})

    with pytest.raises(ValidationError):
        order.full_clean()


@pytest.mark.django_db
def test_database_rejects_negative_shipping_total(customer, address):
    order = build_order(
        customer,
        address,
        shipping_total=Decimal("-1.00"),
        grand_total=Decimal("89.00"),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        order.save()


@pytest.mark.django_db
def test_totals_do_not_assume_future_discount_scope(customer, address):
    order = build_order(
        customer,
        address,
        discount_total=Decimal("110.00"),
        shipping_total=Decimal("20.00"),
        grand_total=Decimal("10.00"),
    )

    order.full_clean()
    order.save()

    assert order.grand_total == Decimal("10.00")


@pytest.mark.django_db
def test_database_rejects_inconsistent_grand_total(customer, address):
    order = build_order(customer, address, grand_total=Decimal("96.00"))

    with pytest.raises(IntegrityError), transaction.atomic():
        order.save()


@pytest.mark.django_db
def test_fractional_rial_order_total_fails_model_validation(customer, address):
    order = build_order(
        customer,
        address,
        subtotal=Decimal("100.50"),
        grand_total=Decimal("95.50"),
    )

    with pytest.raises(ValidationError) as exc_info:
        order.full_clean()

    assert "subtotal" in exc_info.value.message_dict
    assert "grand_total" in exc_info.value.message_dict


@pytest.mark.django_db
def test_fractional_rial_order_total_is_rejected_by_database(customer, address):
    order = build_order(
        customer,
        address,
        subtotal=Decimal("100.50"),
        grand_total=Decimal("95.50"),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        order.save()


@pytest.mark.django_db
def test_zero_value_order_is_allowed(customer, address):
    order = build_order(
        customer,
        address,
        subtotal=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        shipping_total=Decimal("0.00"),
        grand_total=Decimal("0.00"),
    )

    order.full_clean()
    order.save()

    assert order.grand_total == Decimal("0.00")


@pytest.mark.django_db
def test_order_item_preserves_product_snapshot_after_change_and_delete(
    customer,
    address,
    product,
):
    order = build_order(customer, address)
    order.save()
    item = OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        sku=product.sku,
        unit_price=product.price,
        quantity=4,
        line_total=Decimal("100.00"),
    )

    product.name = "Renamed product"
    product.sku = "RENAMED-SKU"
    product.price = Decimal("30.00")
    product.save()
    product.delete()
    item.refresh_from_db()

    assert item.product is None
    assert item.product_name == "Historical product"
    assert item.sku == "HISTORICAL-SKU"
    assert item.unit_price == Decimal("25.00")
    assert item.line_total == Decimal("100.00")


@pytest.mark.django_db
def test_deleting_order_cascades_to_items(customer, address, product):
    order = build_order(customer, address)
    order.save()
    item = OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        sku=product.sku,
        unit_price=product.price,
        quantity=1,
        line_total=product.price,
    )

    order.delete()

    assert OrderItem.objects.filter(pk=item.pk).exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [0, -1])
def test_database_rejects_nonpositive_item_quantity(
    customer,
    address,
    product,
    quantity,
):
    order = build_order(customer, address)
    order.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            sku=product.sku,
            unit_price=product.price,
            quantity=quantity,
            line_total=Decimal("0.00"),
        )


@pytest.mark.django_db
def test_database_rejects_negative_item_money(customer, address, product):
    order = build_order(customer, address)
    order.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            sku=product.sku,
            unit_price=Decimal("-1.00"),
            quantity=1,
            line_total=Decimal("-1.00"),
        )


@pytest.mark.django_db
def test_database_rejects_inconsistent_line_total(customer, address, product):
    order = build_order(customer, address)
    order.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            sku=product.sku,
            unit_price=Decimal("25.00"),
            quantity=2,
            line_total=Decimal("49.00"),
        )


@pytest.mark.django_db
def test_fractional_rial_order_item_is_rejected_by_database(
    customer,
    address,
    product,
):
    order = build_order(customer, address)
    order.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            sku=product.sku,
            unit_price=Decimal("25.50"),
            quantity=2,
            line_total=Decimal("51.00"),
        )


@pytest.mark.django_db
def test_zero_unit_price_and_line_total_are_allowed(customer, address, product):
    order = build_order(customer, address)
    order.save()

    item = OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        sku=product.sku,
        unit_price=Decimal("0.00"),
        quantity=1,
        line_total=Decimal("0.00"),
    )

    assert item.pk is not None
