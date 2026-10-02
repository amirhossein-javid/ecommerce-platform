from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User


@pytest.mark.django_db
def test_profile_has_one_to_one_relationship_with_user():
    user = User.objects.create_user("customer@example.com")
    profile = CustomerProfile.objects.create(user=user)

    assert user.customer_profile == profile

    with pytest.raises(IntegrityError), transaction.atomic():
        CustomerProfile.objects.create(user=user)


@pytest.mark.django_db
def test_deleting_user_cascades_to_profile():
    user = User.objects.create_user("customer@example.com")
    profile = CustomerProfile.objects.create(user=user)

    user.delete()

    assert CustomerProfile.objects.filter(pk=profile.pk).exists() is False


@pytest.mark.django_db
def test_deleting_profile_does_not_delete_user():
    user = User.objects.create_user("customer@example.com")
    profile = CustomerProfile.objects.create(user=user)

    profile.delete()

    assert User.objects.filter(pk=user.pk).exists() is True


@pytest.mark.django_db
def test_name_fields_are_optional():
    user = User.objects.create_user("customer@example.com")
    profile = CustomerProfile(user=user)

    profile.full_clean()
    profile.save()

    assert profile.first_name == ""
    assert profile.last_name == ""


@pytest.mark.django_db
def test_duplicate_phone_numbers_are_allowed():
    first_user = User.objects.create_user("first@example.com")
    second_user = User.objects.create_user("second@example.com")

    first_profile = CustomerProfile.objects.create(
        user=first_user,
        phone_number="+14155552671",
    )
    second_profile = CustomerProfile.objects.create(
        user=second_user,
        phone_number="+14155552671",
    )

    assert first_profile.phone_number == second_profile.phone_number


@pytest.mark.django_db
def test_timestamps_are_set_and_updated():
    user = User.objects.create_user("customer@example.com")
    profile = CustomerProfile.objects.create(user=user)
    original_created_at = profile.created_at
    stale_updated_at = timezone.now() - timedelta(days=1)
    CustomerProfile.objects.filter(pk=profile.pk).update(
        updated_at=stale_updated_at,
    )

    profile.first_name = "Updated"
    profile.save()
    profile.refresh_from_db()

    assert profile.created_at == original_created_at
    assert profile.updated_at > stale_updated_at


@pytest.mark.django_db
def test_user_can_exist_without_profile():
    user = User.objects.create_user("customer@example.com")

    assert CustomerProfile.objects.filter(user=user).exists() is False

    with pytest.raises(CustomerProfile.DoesNotExist):
        _ = user.customer_profile
