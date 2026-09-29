from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.products.models import Category, Product


@pytest.fixture
def category(db):
    return Category.objects.create(name="Electronics")


def build_product(category, **overrides):
    values = {
        "category": category,
        "name": "Laptop",
        "sku": "LAPTOP-001",
        "price": Decimal("1299.99"),
    }
    values.update(overrides)
    return Product(**values)


@pytest.mark.django_db
def test_product_defaults_and_string_representation(category):
    product = build_product(category)
    product.save()

    assert product.slug == "laptop"
    assert product.description == ""
    assert product.stock_quantity == 0
    assert product.status == Product.Status.DRAFT
    assert str(product) == "Laptop"


@pytest.mark.django_db
def test_product_belongs_to_category(category):
    product = build_product(category)
    product.save()

    assert product.category == category
    assert list(category.products.all()) == [product]


@pytest.mark.django_db
def test_deleting_category_with_products_is_protected(category):
    product = build_product(category)
    product.save()

    with pytest.raises(ProtectedError):
        category.delete()

    assert Product.objects.filter(pk=product.pk).exists() is True


@pytest.mark.django_db
def test_product_required_fields_are_validated(category):
    product = Product(category=category)

    with pytest.raises(ValidationError) as exc_info:
        product.full_clean()

    assert {"name", "sku", "price"} <= exc_info.value.message_dict.keys()


@pytest.mark.django_db
def test_category_is_required_by_model_validation():
    product = Product(name="Laptop", sku="LAPTOP-001", price=Decimal("1.00"))

    with pytest.raises(ValidationError) as exc_info:
        product.full_clean()

    assert "category" in exc_info.value.message_dict


@pytest.mark.django_db
def test_product_names_are_not_unique(category):
    first = build_product(category, sku="LAPTOP-001", slug="first-laptop")
    second = build_product(category, sku="LAPTOP-002", slug="second-laptop")

    Product.objects.bulk_create([first, second])

    assert Product.objects.filter(name="Laptop").count() == 2


@pytest.mark.django_db
def test_description_is_optional(category):
    product = build_product(category, description="")

    product.full_clean()
    product.save()

    assert product.description == ""


@pytest.mark.django_db
def test_product_timestamps_are_set_and_updated(category):
    product = build_product(category)
    product.save()
    original_created_at = product.created_at
    stale_updated_at = timezone.now() - timedelta(days=1)
    Product.objects.filter(pk=product.pk).update(updated_at=stale_updated_at)

    product.description = "Updated description"
    product.save()
    product.refresh_from_db()

    assert product.created_at == original_created_at
    assert product.updated_at > stale_updated_at


@pytest.mark.django_db
def test_missing_slug_is_generated_from_name(category):
    product = build_product(category, name="Gaming Laptop")

    product.save()

    assert product.slug == "gaming-laptop"


@pytest.mark.django_db
def test_full_clean_generates_missing_slug(category):
    product = build_product(category, name="Gaming Laptop")

    product.full_clean()

    assert product.slug == "gaming-laptop"


@pytest.mark.django_db
def test_explicit_slug_is_preserved(category):
    product = build_product(category, slug="portable-computer")

    product.save()

    assert product.slug == "portable-computer"


@pytest.mark.django_db
def test_slug_stays_stable_when_name_changes(category):
    product = build_product(category, name="Gaming Laptop")
    product.save()

    product.name = "Professional Laptop"
    product.save()
    product.refresh_from_db()

    assert product.slug == "gaming-laptop"


@pytest.mark.django_db
def test_generated_slug_collision_surfaces_unique_constraint(category):
    first = build_product(category, sku="LAPTOP-001")
    second = build_product(category, sku="LAPTOP-002")
    first.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        second.save()


@pytest.mark.django_db
def test_name_that_cannot_produce_slug_is_rejected(category):
    product = build_product(category, name="!!!")

    with pytest.raises(ValidationError) as exc_info:
        product.save()

    assert "slug" in exc_info.value.message_dict


@pytest.mark.django_db
def test_explicit_slug_is_validated_on_save(category):
    product = build_product(category, slug="not a valid slug")

    with pytest.raises(ValidationError) as exc_info:
        product.save()

    assert "slug" in exc_info.value.message_dict


@pytest.mark.django_db
def test_sku_is_case_insensitively_unique_in_database(category):
    build_product(category, sku="LAPTOP-001", slug="first-laptop").save()

    with pytest.raises(IntegrityError), transaction.atomic():
        build_product(category, sku="laptop-001", slug="second-laptop").save()


@pytest.mark.django_db
def test_sku_case_is_preserved(category):
    product = build_product(category, sku="LapTop-001")

    product.save()
    product.refresh_from_db()

    assert product.sku == "LapTop-001"


@pytest.mark.django_db
def test_sku_accepts_64_characters(category):
    product = build_product(category, sku="S" * 64)

    product.full_clean()

    assert product.sku == "S" * 64


@pytest.mark.django_db
def test_sku_rejects_more_than_64_characters(category):
    product = build_product(category, sku="S" * 65)

    with pytest.raises(ValidationError) as exc_info:
        product.full_clean()

    assert "sku" in exc_info.value.message_dict


@pytest.mark.django_db
def test_full_clean_detects_case_insensitive_duplicate_sku(category):
    build_product(category, sku="LAPTOP-001", slug="first-laptop").save()
    duplicate = build_product(
        category,
        sku="laptop-001",
        slug="second-laptop",
    )

    with pytest.raises(ValidationError) as exc_info:
        duplicate.full_clean()

    assert "__all__" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("price", [Decimal("0.00"), Decimal("-0.01")])
def test_nonpositive_price_fails_model_validation(category, price):
    product = build_product(category, price=price)

    with pytest.raises(ValidationError) as exc_info:
        product.full_clean()

    assert "price" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("price", [Decimal("0.00"), Decimal("-0.01")])
def test_nonpositive_price_is_rejected_by_database(category, price):
    product = build_product(category, price=price)

    with pytest.raises(IntegrityError), transaction.atomic():
        product.save()


@pytest.mark.django_db
def test_negative_stock_fails_model_validation(category):
    product = build_product(category, stock_quantity=-1)

    with pytest.raises(ValidationError) as exc_info:
        product.full_clean()

    assert "stock_quantity" in exc_info.value.message_dict


@pytest.mark.django_db
def test_negative_stock_is_rejected_by_database(category):
    product = build_product(category, stock_quantity=-1)

    with pytest.raises(IntegrityError), transaction.atomic():
        product.save()


@pytest.mark.django_db
@pytest.mark.parametrize("status", list(Product.Status.values))
def test_all_product_statuses_are_valid(category, status):
    product = build_product(category, status=status)

    product.full_clean()

    assert product.status == status


@pytest.mark.django_db
def test_invalid_status_fails_model_validation(category):
    product = build_product(category, status="UNKNOWN")

    with pytest.raises(ValidationError) as exc_info:
        product.full_clean()

    assert "status" in exc_info.value.message_dict


@pytest.mark.django_db
def test_active_product_can_have_zero_stock(category):
    product = build_product(
        category,
        status=Product.Status.ACTIVE,
        stock_quantity=0,
    )

    product.full_clean()
    product.save()

    assert product.status == Product.Status.ACTIVE
    assert product.stock_quantity == 0
