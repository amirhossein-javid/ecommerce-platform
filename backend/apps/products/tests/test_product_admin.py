from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Event

import pytest
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.orders.lifecycle import cancel_order
from apps.orders.models import (
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from apps.payments.gateways import PaymentVerification, VerificationStatus
from apps.payments.models import PaymentAttempt
from apps.payments.services import finalize_verified_payment
from apps.products.admin import CategoryAdmin, ProductAdmin, ProductImageInline
from apps.products.models import Category, Product, ProductImage

GIF_IMAGE = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00"
    b"\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        "admin@example.com",
        "strong-password",
    )


@pytest.fixture
def product(db):
    category = Category.objects.create(name="Electronics")
    return Product.objects.create(
        category=category,
        name="Laptop",
        sku="LAPTOP-001",
        price=Decimal("1299.00"),
    )


def product_form_data(product, images):
    data = {
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku,
        "category": product.category_id,
        "status": product.status,
        "description": product.description,
        "price": product.price,
        "stock_quantity": product.stock_quantity,
        "images-TOTAL_FORMS": len(images) + 1,
        "images-INITIAL_FORMS": len(images),
        "images-MIN_NUM_FORMS": 0,
        "images-MAX_NUM_FORMS": 1000,
    }
    for index, image in enumerate(images):
        data.update(
            {
                f"images-{index}-id": image.pk,
                f"images-{index}-product": product.pk,
                f"images-{index}-alt_text": image.alt_text,
                f"images-{index}-position": image.position,
            }
        )
        if image.is_primary:
            data[f"images-{index}-is_primary"] = "on"
    extra_index = len(images)
    data.update(
        {
            f"images-{extra_index}-product": product.pk,
            f"images-{extra_index}-alt_text": "",
            f"images-{extra_index}-position": 0,
        }
    )
    return data


def create_image(product, position, *, is_primary=False, alt_text=""):
    return ProductImage.objects.create(
        product=product,
        image=f"products/{product.pk}/image-{position}.jpg",
        alt_text=alt_text,
        position=position,
        is_primary=is_primary,
    )


def product_changelist_data(product):
    return {
        "form-TOTAL_FORMS": 1,
        "form-INITIAL_FORMS": 1,
        "form-MIN_NUM_FORMS": 0,
        "form-MAX_NUM_FORMS": 1000,
        "form-0-id": product.pk,
        "form-0-status": Product.Status.ARCHIVED,
        "_save": "Save",
    }


def test_category_and_product_use_custom_admins_with_product_image_inline():
    assert isinstance(admin.site._registry[Category], CategoryAdmin)
    product_admin = admin.site._registry[Product]
    assert isinstance(product_admin, ProductAdmin)
    assert ProductImageInline in product_admin.inlines
    assert ProductImage not in admin.site._registry


def test_admin_configuration_supports_catalog_management():
    category_admin = admin.site._registry[Category]
    product_admin = admin.site._registry[Product]

    assert category_admin.search_fields == ("name", "slug")
    assert category_admin.list_filter == ("is_active",)
    assert category_admin.prepopulated_fields == {"slug": ("name",)}
    assert product_admin.search_fields == ("name", "sku", "slug")
    assert product_admin.list_filter == ("status", "category")
    assert product_admin.list_editable == ("status",)
    assert product_admin.prepopulated_fields == {"slug": ("name",)}


@pytest.mark.django_db
def test_superuser_can_open_category_and_product_admin_pages(
    client,
    superuser,
    product,
):
    client.force_login(superuser)

    category_response = client.get(reverse("admin:products_category_changelist"))
    product_response = client.get(reverse("admin:products_product_changelist"))
    change_response = client.get(
        reverse("admin:products_product_change", args=(product.pk,))
    )

    assert category_response.status_code == 200
    assert product_response.status_code == 200
    assert change_response.status_code == 200
    assert b"Laptop" in product_response.content
    assert b"images-0-image" in change_response.content
    assert b"images-0-alt_text" in change_response.content
    assert b"images-0-position" in change_response.content
    assert b"images-0-is_primary" in change_response.content


@pytest.mark.django_db
def test_category_admin_returns_parent_cycle_as_form_error(client, superuser):
    root = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Computers", parent=root)
    client.force_login(superuser)

    response = client.post(
        reverse("admin:products_category_change", args=(root.pk,)),
        {
            "name": root.name,
            "slug": root.slug,
            "parent": child.pk,
            "is_active": "on",
            "_save": "Save",
        },
    )

    assert response.status_code == 200
    assert "parent" in response.context["adminform"].form.errors
    root.refresh_from_db()
    assert root.parent is None


@pytest.mark.django_db
def test_product_changelist_displays_primary_image_thumbnail(
    client,
    superuser,
    product,
):
    image = create_image(product, 0, alt_text="Front view")
    client.force_login(superuser)

    response = client.get(reverse("admin:products_product_changelist"))

    assert response.status_code == 200
    assert image.image.url.encode() in response.content
    assert b"Front view" in response.content


@pytest.mark.django_db
def test_admin_inline_first_image_becomes_primary(
    client,
    superuser,
    product,
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(superuser)
    data = product_form_data(product, [])
    data.update(
        {
            "images-0-image": SimpleUploadedFile(
                "front.gif",
                GIF_IMAGE,
                content_type="image/gif",
            ),
            "images-0-alt_text": "Front view",
            "images-0-position": 0,
        }
    )

    response = client.post(
        reverse("admin:products_product_change", args=(product.pk,)),
        data,
    )

    assert response.status_code == 302
    image = product.images.get()
    assert image.is_primary is True
    assert image.alt_text == "Front view"


@pytest.mark.django_db
def test_admin_inline_can_change_primary_image(client, superuser, product):
    first = create_image(product, 0)
    second = create_image(product, 1)
    client.force_login(superuser)
    data = product_form_data(product, [first, second])
    data["images-1-is_primary"] = "on"

    response = client.post(
        reverse("admin:products_product_change", args=(product.pk,)),
        data,
    )

    assert response.status_code == 302
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary is False
    assert second.is_primary is True


@pytest.mark.django_db
def test_admin_inline_rejects_multiple_new_primary_selections(
    client,
    superuser,
    product,
):
    first = create_image(product, 0)
    second = create_image(product, 1)
    third = create_image(product, 2)
    client.force_login(superuser)
    data = product_form_data(product, [first, second, third])
    data["images-1-is_primary"] = "on"
    data["images-2-is_primary"] = "on"

    response = client.post(
        reverse("admin:products_product_change", args=(product.pk,)),
        data,
    )

    assert response.status_code == 200
    assert "فقط یک تصویر اصلی جدید انتخاب کنید." in response.content.decode()
    first.refresh_from_db()
    second.refresh_from_db()
    third.refresh_from_db()
    assert first.is_primary is True
    assert second.is_primary is False
    assert third.is_primary is False


@pytest.mark.django_db
def test_admin_inline_deleting_primary_promotes_lowest_position(
    client,
    superuser,
    product,
):
    primary = create_image(product, 5)
    lowest = create_image(product, 1)
    other = create_image(product, 3)
    client.force_login(superuser)
    data = product_form_data(product, [primary, lowest, other])
    data["images-0-DELETE"] = "on"
    data["images-1-alt_text"] = "Updated front view"

    response = client.post(
        reverse("admin:products_product_change", args=(product.pk,)),
        data,
    )

    assert response.status_code == 302
    assert ProductImage.objects.filter(pk=primary.pk).exists() is False
    lowest.refresh_from_db()
    other.refresh_from_db()
    assert lowest.is_primary is True
    assert lowest.alt_text == "Updated front view"
    assert other.is_primary is False


@pytest.mark.django_db
def test_admin_cannot_reduce_stock_below_active_reservations(
    client,
    superuser,
    product,
):
    customer = CustomerProfile.objects.create(
        user=User.objects.create_user("customer@example.com")
    )
    order = Order.objects.create(
        customer=customer,
        subtotal=Decimal("1299"),
        grand_total=Decimal("1299"),
        shipping_recipient_first_name="Customer",
        shipping_recipient_last_name="Name",
        shipping_recipient_phone_number="+989121234567",
        shipping_province="Tehran",
        shipping_city="Tehran",
        shipping_address="Address",
        shipping_postal_code="1234567890",
    )
    product.stock_quantity = 10
    product.save(update_fields=("stock_quantity",))
    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=6,
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    client.force_login(superuser)
    data = product_form_data(product, [])
    data["stock_quantity"] = 5

    response = client.post(
        reverse("admin:products_product_change", args=(product.pk,)),
        data,
    )

    assert response.status_code == 200
    assert "موجودی نمی‌تواند از تعداد رزروشده فعال کمتر باشد" in (
        response.content.decode()
    )
    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_product_changelist_changes_status_without_accepting_stock(
    client, superuser, product
):
    client.force_login(superuser)
    original_stock = product.stock_quantity
    original_updated_at = product.updated_at
    data = product_changelist_data(product)
    data["form-0-stock_quantity"] = 999

    response = client.post(reverse("admin:products_product_changelist"), data)

    assert response.status_code == 302
    product.refresh_from_db()
    assert product.status == Product.Status.ARCHIVED
    assert product.stock_quantity == original_stock
    assert product.updated_at > original_updated_at


@pytest.mark.django_db
def test_product_change_form_preserves_status_and_explicit_stock_management(
    client, superuser, product
):
    client.force_login(superuser)
    data = product_form_data(product, [])
    data.update(status=Product.Status.ACTIVE, stock_quantity=12)

    response = client.post(
        reverse("admin:products_product_change", args=(product.pk,)), data
    )

    assert response.status_code == 302
    product.refresh_from_db()
    assert product.status == Product.Status.ACTIVE
    assert product.stock_quantity == 12


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("inventory_operation", ("payment", "cancellation"))
def test_product_changelist_preserves_concurrent_inventory_commit(
    superuser, product, monkeypatch, inventory_operation
):
    product.status = Product.Status.ACTIVE
    product.stock_quantity = 10
    product.save(update_fields=("status", "stock_quantity"))
    customer = CustomerProfile.objects.create(
        user=User.objects.create_user("inventory-race@example.com")
    )
    order = Order.objects.create(
        customer=customer, subtotal=product.price, grand_total=product.price
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        sku=product.sku,
        unit_price=product.price,
        quantity=1,
        line_total=product.price,
    )
    reservation = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    attempt = PaymentAttempt.objects.create(
        order=order, amount=order.grand_total, gateway="test", gateway_reference="race"
    )
    verification = PaymentVerification(
        status=VerificationStatus.SUCCESS,
        gateway_reference=attempt.gateway_reference,
        amount=attempt.amount,
        currency=attempt.currency,
    )
    if inventory_operation == "cancellation":
        finalize_verified_payment(attempt=attempt, verification=verification)
        product.refresh_from_db()

    original_stock = product.stock_quantity
    loaded = Event()
    resume_save = Event()
    worker_state = {}
    product_admin = admin.site._registry[Product]
    save_model = product_admin.save_model

    def pause_before_save(request, obj, form, change):
        # Only control scheduling: the request, database, and domain services are real.
        worker_state["stock"] = obj.stock_quantity
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            worker_state["pid"] = cursor.fetchone()[0]
        loaded.set()
        assert resume_save.wait(timeout=10)
        return save_model(request, obj, form, change)

    monkeypatch.setattr(product_admin, "save_model", pause_before_save)

    def edit_status():
        try:
            client = Client()
            client.force_login(User.objects.get(pk=superuser.pk))
            return client.post(
                reverse("admin:products_product_changelist"),
                product_changelist_data(product),
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(edit_status)
        try:
            assert loaded.wait(timeout=10)
            assert worker_state["stock"] == original_stock
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                assert cursor.fetchone()[0] != worker_state["pid"]
            if inventory_operation == "payment":
                finalize_verified_payment(attempt=attempt, verification=verification)
                expected_stock = 9
            else:
                result = cancel_order(
                    order=order,
                    actor_type=OrderStatusHistory.ActorType.OPERATOR,
                    actor_user=superuser,
                )
                assert result.changed is True
                expected_stock = 10
            # The inventory transaction must commit before the stale Admin save.
            assert Product.objects.get(pk=product.pk).stock_quantity == expected_stock
        finally:
            resume_save.set()
        assert future.result(timeout=10) == 302

    product.refresh_from_db()
    order.refresh_from_db()
    reservation.refresh_from_db()
    attempt.refresh_from_db()
    assert product.status == Product.Status.ARCHIVED
    assert product.stock_quantity == expected_stock
    assert attempt.status == PaymentAttempt.Status.SUCCESS
    assert reservation.status == InventoryReservation.Status.CONSUMED
    if inventory_operation == "payment":
        assert order.status == Order.Status.PAID
        assert order.refund_status == Order.RefundStatus.NOT_REQUIRED
    else:
        assert order.status == Order.Status.CANCELLED
        assert order.refund_status == Order.RefundStatus.REQUIRED
        replay = cancel_order(
            order=order,
            actor_type=OrderStatusHistory.ActorType.OPERATOR,
            actor_user=superuser,
        )
        assert replay.changed is False
        product.refresh_from_db()
        assert product.stock_quantity == expected_stock
