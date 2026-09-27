from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.products.models import Category


@pytest.mark.django_db
def test_category_defaults_and_string_representation():
    category = Category.objects.create(name="Electronics")

    assert category.slug == "electronics"
    assert category.parent is None
    assert category.is_active is True
    assert str(category) == "Electronics"


@pytest.mark.django_db
def test_category_can_have_parent_and_children():
    parent = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Laptops", parent=parent)

    assert child.parent == parent
    assert list(parent.children.all()) == [child]


@pytest.mark.django_db
def test_category_can_be_inactive():
    category = Category.objects.create(name="Archived", is_active=False)

    assert category.is_active is False


@pytest.mark.django_db
def test_category_timestamps_are_set_and_updated():
    category = Category.objects.create(name="Electronics")
    original_created_at = category.created_at
    stale_updated_at = timezone.now() - timedelta(days=1)
    Category.objects.filter(pk=category.pk).update(updated_at=stale_updated_at)

    category.name = "Consumer Electronics"
    category.save()
    category.refresh_from_db()

    assert category.created_at == original_created_at
    assert category.updated_at > stale_updated_at


@pytest.mark.django_db
def test_deleting_category_with_children_is_protected():
    parent = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Laptops", parent=parent)

    with pytest.raises(ProtectedError):
        parent.delete()

    assert Category.objects.filter(pk=parent.pk).exists() is True
    assert Category.objects.filter(pk=child.pk).exists() is True


@pytest.mark.django_db
def test_category_without_children_can_be_deleted():
    category = Category.objects.create(name="Electronics")

    category.delete()

    assert Category.objects.filter(pk=category.pk).exists() is False


@pytest.mark.django_db
def test_direct_self_parenting_is_rejected():
    category = Category.objects.create(name="Electronics")
    category.parent = category

    with pytest.raises(ValidationError) as exc_info:
        category.save()

    assert "parent" in exc_info.value.message_dict


@pytest.mark.django_db
def test_database_constraint_rejects_direct_self_parenting():
    category = Category.objects.create(name="Electronics")

    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.filter(pk=category.pk).update(parent_id=category.pk)


@pytest.mark.django_db
def test_deeper_category_cycle_is_rejected():
    root = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Computers", parent=root)
    grandchild = Category.objects.create(name="Laptops", parent=child)
    root.parent = grandchild

    with pytest.raises(ValidationError) as exc_info:
        root.save()

    assert "parent" in exc_info.value.message_dict


@pytest.mark.django_db
def test_parent_change_is_ignored_when_excluded_from_update_fields():
    root = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Computers", parent=root)
    root.parent = child
    root.name = "Consumer Electronics"

    root.save(update_fields=["name"])
    root.refresh_from_db()

    assert root.name == "Consumer Electronics"
    assert root.parent is None


@pytest.mark.django_db
def test_parent_change_is_validated_when_included_in_update_fields():
    root = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Computers", parent=root)
    root.parent = child

    with pytest.raises(ValidationError) as exc_info:
        root.save(update_fields=["parent"])

    assert "parent" in exc_info.value.message_dict


@pytest.mark.django_db
def test_full_clean_rejects_category_cycle():
    root = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Computers", parent=root)
    root.parent = child

    with pytest.raises(ValidationError) as exc_info:
        root.full_clean()

    assert "parent" in exc_info.value.message_dict


@pytest.mark.django_db
def test_slug_is_generated_from_name_when_omitted():
    category = Category.objects.create(name="Home Appliances")

    assert category.slug == "home-appliances"


@pytest.mark.django_db
def test_full_clean_generates_slug_from_name_when_omitted():
    category = Category(name="Home Appliances")

    category.full_clean()

    assert category.slug == "home-appliances"


@pytest.mark.django_db
def test_generated_slug_supports_unicode_names():
    category = Category.objects.create(name="لوازم خانگی")

    assert category.slug == "لوازم-خانگی"


@pytest.mark.django_db
def test_explicit_slug_is_preserved():
    category = Category.objects.create(
        name="Home Appliances",
        slug="major-appliances",
    )

    assert category.slug == "major-appliances"


@pytest.mark.django_db
def test_slug_stays_stable_when_name_changes():
    category = Category.objects.create(name="Home Appliances")

    category.name = "Kitchen Appliances"
    category.save()
    category.refresh_from_db()

    assert category.slug == "home-appliances"


@pytest.mark.django_db
def test_slug_change_is_ignored_when_excluded_from_update_fields():
    category = Category.objects.create(name="Home Appliances")
    category.slug = ""
    category.name = "Kitchen Appliances"

    category.save(update_fields=["name"])
    category.refresh_from_db()

    assert category.slug == "home-appliances"


@pytest.mark.django_db
def test_generated_slug_collision_surfaces_unique_constraint():
    Category.objects.create(name="Home Appliances")

    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.create(name="Home Appliances")


@pytest.mark.django_db
def test_explicit_slug_must_be_globally_unique():
    Category.objects.create(name="Computers", slug="technology")

    with pytest.raises(IntegrityError), transaction.atomic():
        Category.objects.create(name="Phones", slug="technology")


@pytest.mark.django_db
def test_duplicate_names_are_allowed_when_slugs_differ():
    first = Category.objects.create(name="Accessories", slug="phone-accessories")
    second = Category.objects.create(name="Accessories", slug="laptop-accessories")

    assert first.name == second.name


@pytest.mark.django_db
def test_name_that_cannot_produce_slug_is_rejected():
    category = Category(name="!!!")

    with pytest.raises(ValidationError) as exc_info:
        category.save()

    assert "slug" in exc_info.value.message_dict


@pytest.mark.django_db
def test_full_clean_rejects_name_that_cannot_produce_slug():
    category = Category(name="!!!")

    with pytest.raises(ValidationError) as exc_info:
        category.full_clean()

    assert "slug" in exc_info.value.message_dict


@pytest.mark.django_db
def test_category_name_is_required_by_model_validation():
    category = Category(name="")

    with pytest.raises(ValidationError) as exc_info:
        category.full_clean()

    assert "name" in exc_info.value.message_dict


@pytest.mark.django_db
def test_explicit_slug_is_validated():
    category = Category(name="Electronics", slug="not a valid slug")

    with pytest.raises(ValidationError) as exc_info:
        category.full_clean()

    assert "slug" in exc_info.value.message_dict


@pytest.mark.django_db
def test_save_validates_explicit_slug():
    category = Category(name="Electronics", slug="not a valid slug")

    with pytest.raises(ValidationError) as exc_info:
        category.save()

    assert "slug" in exc_info.value.message_dict


@pytest.mark.django_db
def test_queryset_update_bypasses_deep_cycle_validation():
    root = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Computers", parent=root)
    grandchild = Category.objects.create(name="Laptops", parent=child)

    Category.objects.filter(pk=root.pk).update(parent=grandchild)

    root.refresh_from_db()
    assert root.parent == grandchild


@pytest.mark.django_db
def test_bulk_create_bypasses_slug_generation():
    category = Category(name="Home Appliances")

    Category.objects.bulk_create([category])

    category.refresh_from_db()
    assert category.slug == ""
