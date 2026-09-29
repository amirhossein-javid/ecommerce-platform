from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.products.models import Category, Product, ProductImage

GIF_IMAGE = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00"
    b"\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
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


def build_image(product, position=0, **overrides):
    values = {
        "product": product,
        "image": f"fixtures/product-{product.pk}-{position}.jpg",
        "position": position,
    }
    values.update(overrides)
    return ProductImage(**values)


@pytest.mark.django_db
def test_first_image_automatically_becomes_primary(product):
    image = ProductImage(
        product=product,
        image=f"fixtures/product-{product.pk}-first.jpg",
    )

    image.save()

    assert image.is_primary is True
    assert image.position == 0
    assert product.images.get() == image


@pytest.mark.django_db
def test_product_can_have_multiple_images(product):
    first = build_image(product, position=0)
    second = build_image(product, position=1)
    first.save()
    second.save()

    assert list(product.images.order_by("position")) == [first, second]
    assert first.is_primary is True
    assert second.is_primary is False


@pytest.mark.django_db
def test_explicit_primary_change_unsets_previous_primary(product):
    first = build_image(product, position=0)
    second = build_image(product, position=1)
    first.save()
    second.save()

    second.is_primary = True
    second.save(update_fields=["is_primary"])
    first.refresh_from_db()
    second.refresh_from_db()

    assert first.is_primary is False
    assert second.is_primary is True
    assert product.images.filter(is_primary=True).count() == 1


@pytest.mark.django_db
def test_new_image_can_be_explicitly_made_primary(product):
    first = build_image(product, position=0)
    first.save()

    second = build_image(product, position=1, is_primary=True)
    second.save()
    first.refresh_from_db()

    assert first.is_primary is False
    assert second.is_primary is True


@pytest.mark.django_db
def test_failed_primary_change_rolls_back_previous_primary(product):
    first = build_image(product, position=0)
    second = build_image(product, position=1)
    first.save()
    second.save()
    second.position = 0
    second.is_primary = True

    with pytest.raises(IntegrityError):
        second.save()

    first.refresh_from_db()
    second.refresh_from_db()

    assert first.is_primary is True
    assert second.is_primary is False


@pytest.mark.django_db
def test_deleting_primary_promotes_lowest_position(product):
    primary = build_image(product, position=5)
    lowest = build_image(product, position=1)
    other = build_image(product, position=3)
    primary.save()
    lowest.save()
    other.save()

    primary.delete()
    lowest.refresh_from_db()
    other.refresh_from_db()

    assert lowest.is_primary is True
    assert other.is_primary is False


@pytest.mark.django_db
def test_deleting_nonprimary_does_not_change_primary(product):
    primary = build_image(product, position=0)
    other = build_image(product, position=1)
    primary.save()
    other.save()

    other.delete()
    primary.refresh_from_db()

    assert primary.is_primary is True
    assert product.images.filter(is_primary=True).count() == 1


@pytest.mark.django_db
def test_deleting_final_image_leaves_product_without_images(product):
    image = build_image(product)
    image.save()

    image.delete()

    assert product.images.exists() is False


@pytest.mark.django_db
def test_database_rejects_multiple_primary_images(product):
    build_image(product, position=0).save()
    second = build_image(product, position=1, is_primary=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductImage.objects.bulk_create([second])


@pytest.mark.django_db
def test_database_rejects_duplicate_position_for_product(product):
    build_image(product, position=0).save()
    duplicate = build_image(product, position=0)

    with pytest.raises(IntegrityError), transaction.atomic():
        duplicate.save()


@pytest.mark.django_db
def test_same_position_is_allowed_for_different_products(product):
    second_product = Product.objects.create(
        category=product.category,
        name="Phone",
        sku="PHONE-001",
        price=Decimal("799.99"),
    )

    build_image(product, position=0).save()
    build_image(second_product, position=0).save()

    assert ProductImage.objects.filter(position=0).count() == 2


@pytest.mark.django_db
def test_negative_position_fails_model_validation(product):
    image = build_image(product, position=-1)

    with pytest.raises(ValidationError) as exc_info:
        image.full_clean()

    assert "position" in exc_info.value.message_dict


@pytest.mark.django_db
def test_database_rejects_negative_position(product):
    image = build_image(product, position=-1)

    with pytest.raises(IntegrityError), transaction.atomic():
        image.save()


@pytest.mark.django_db
def test_deleting_product_cascades_to_images(product):
    first = build_image(product, position=0)
    second = build_image(product, position=1)
    first.save()
    second.save()

    product.delete()

    assert ProductImage.objects.filter(pk__in=[first.pk, second.pk]).exists() is False


@pytest.mark.django_db
def test_image_is_required(product):
    image = ProductImage(product=product)

    with pytest.raises(ValidationError) as exc_info:
        image.full_clean()

    assert "image" in exc_info.value.message_dict


@pytest.mark.django_db
def test_alt_text_is_optional_and_limited_to_255_characters(product):
    image = build_image(product, alt_text="")
    image.full_clean()

    image.alt_text = "A" * 256
    with pytest.raises(ValidationError) as exc_info:
        image.full_clean()

    assert "alt_text" in exc_info.value.message_dict


@pytest.mark.django_db
def test_uploaded_image_uses_product_directory(product, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    uploaded_image = SimpleUploadedFile(
        "front.gif",
        GIF_IMAGE,
        content_type="image/gif",
    )
    image = ProductImage(product=product, image=uploaded_image)

    image.save()

    assert image.image.name == f"products/{product.pk}/front.gif"
    assert image.image.storage.exists(image.image.name) is True


@pytest.mark.django_db
def test_product_image_timestamps_are_set_and_updated(product):
    image = build_image(product)
    image.save()
    original_created_at = image.created_at
    stale_updated_at = timezone.now() - timedelta(days=1)
    ProductImage.objects.filter(pk=image.pk).update(updated_at=stale_updated_at)

    image.alt_text = "Front view"
    image.save()
    image.refresh_from_db()

    assert image.created_at == original_created_at
    assert image.updated_at > stale_updated_at
