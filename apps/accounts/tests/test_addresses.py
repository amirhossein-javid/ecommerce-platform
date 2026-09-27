from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Address, CustomerProfile, User


def build_address(profile, **overrides):
    values = {
        "customer_profile": profile,
        "title": "Home",
        "recipient_first_name": "علی",
        "recipient_last_name": "احمدی",
        "recipient_phone_number": "+989121234567",
        "province": "تهران",
        "city": "تهران",
        "address": "خیابان آزادی، کوچه یک، پلاک ۲",
        "postal_code": "1234567890",
    }
    values.update(overrides)
    return Address(**values)


@pytest.fixture
def customer_profile(db):
    user = User.objects.create_user("customer@example.com")
    return CustomerProfile.objects.create(user=user)


@pytest.mark.django_db
def test_profile_can_have_multiple_addresses(customer_profile):
    first_address = build_address(customer_profile, title="Home")
    second_address = build_address(customer_profile, title="Work")
    Address.objects.bulk_create([first_address, second_address])

    assert list(customer_profile.addresses.order_by("title")) == [
        first_address,
        second_address,
    ]


@pytest.mark.django_db
def test_deleting_profile_cascades_to_addresses(customer_profile):
    address = build_address(customer_profile)
    address.save()

    customer_profile.delete()

    assert Address.objects.filter(pk=address.pk).exists() is False


@pytest.mark.django_db
def test_deleting_address_does_not_delete_profile_or_user(customer_profile):
    profile_pk = customer_profile.pk
    user_pk = customer_profile.user_id
    address = build_address(customer_profile)
    address.save()

    address.delete()

    assert CustomerProfile.objects.filter(pk=profile_pk).exists() is True
    assert User.objects.filter(pk=user_pk).exists() is True


@pytest.mark.django_db
def test_valid_address_accepts_persian_text(customer_profile):
    address = build_address(customer_profile)

    address.full_clean()
    address.save()

    assert address.pk is not None


@pytest.mark.django_db
def test_title_is_optional(customer_profile):
    address = build_address(customer_profile, title="")

    address.full_clean()
    address.save()

    assert address.title == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "recipient_first_name",
        "recipient_last_name",
        "recipient_phone_number",
        "province",
        "city",
        "address",
        "postal_code",
    ],
)
def test_required_address_fields_reject_blank_values(customer_profile, field):
    address = build_address(customer_profile, **{field: ""})

    with pytest.raises(ValidationError) as exc_info:
        address.full_clean()

    assert field in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("recipient_phone_number", "09121234567"),
        ("postal_code", "12345-67890"),
    ],
)
def test_address_rejects_invalid_phone_and_postal_code(
    customer_profile,
    field,
    value,
):
    address = build_address(customer_profile, **{field: value})

    with pytest.raises(ValidationError) as exc_info:
        address.full_clean()

    assert field in exc_info.value.message_dict


@pytest.mark.django_db
def test_multiple_nondefault_addresses_are_allowed(customer_profile):
    first_address = build_address(customer_profile, title="Home")
    second_address = build_address(customer_profile, title="Work")

    Address.objects.bulk_create([first_address, second_address])

    assert customer_profile.addresses.filter(is_default=False).count() == 2


@pytest.mark.django_db
def test_second_default_address_for_same_profile_is_rejected(customer_profile):
    build_address(customer_profile, title="Home", is_default=True).save()

    with pytest.raises(IntegrityError), transaction.atomic():
        build_address(customer_profile, title="Work", is_default=True).save()


@pytest.mark.django_db
def test_different_profiles_can_each_have_a_default_address():
    first_user = User.objects.create_user("first@example.com")
    second_user = User.objects.create_user("second@example.com")
    first_profile = CustomerProfile.objects.create(user=first_user)
    second_profile = CustomerProfile.objects.create(user=second_user)

    first_address = build_address(first_profile, is_default=True)
    second_address = build_address(second_profile, is_default=True)
    first_address.save()
    second_address.save()

    assert first_address.is_default is True
    assert second_address.is_default is True


@pytest.mark.django_db
def test_deleting_default_address_does_not_promote_another(customer_profile):
    default_address = build_address(
        customer_profile,
        title="Home",
        is_default=True,
    )
    other_address = build_address(customer_profile, title="Work")
    default_address.save()
    other_address.save()

    default_address.delete()
    other_address.refresh_from_db()

    assert other_address.is_default is False


@pytest.mark.django_db
def test_first_address_is_not_automatically_default(customer_profile):
    address = build_address(customer_profile)
    address.save()

    assert address.is_default is False


@pytest.mark.django_db
def test_duplicate_titles_and_phone_numbers_are_allowed(customer_profile):
    first_address = build_address(customer_profile)
    second_address = build_address(customer_profile)

    Address.objects.bulk_create([first_address, second_address])

    assert customer_profile.addresses.count() == 2


@pytest.mark.django_db
def test_address_timestamps_are_set_and_updated(customer_profile):
    address = build_address(customer_profile)
    address.save()
    original_created_at = address.created_at
    stale_updated_at = timezone.now() - timedelta(days=1)
    Address.objects.filter(pk=address.pk).update(updated_at=stale_updated_at)

    address.city = "کرج"
    address.save()
    address.refresh_from_db()

    assert address.created_at == original_created_at
    assert address.updated_at > stale_updated_at
