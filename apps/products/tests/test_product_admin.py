from decimal import Decimal

import pytest
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
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
        price=Decimal("1299.99"),
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
    assert b"Select only one new primary image." in response.content
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
