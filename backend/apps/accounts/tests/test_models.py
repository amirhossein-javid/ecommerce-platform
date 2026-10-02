import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User


def test_get_user_model_resolves_to_accounts_user():
    assert get_user_model() is User


def test_user_uses_email_as_its_only_login_identifier():
    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []

    with pytest.raises(FieldDoesNotExist):
        User._meta.get_field("username")


@pytest.mark.django_db
def test_user_string_representation_is_email():
    user = User.objects.create_user("customer@example.com")

    assert str(user) == "customer@example.com"


@pytest.mark.django_db
def test_direct_model_save_normalizes_email():
    user = User(email="  Customer@EXAMPLE.COM ")
    user.set_password("strong-password")
    user.save()

    user.refresh_from_db()

    assert user.email == "customer@example.com"


@pytest.mark.django_db
def test_email_is_unique_regardless_of_case():
    User.objects.create(email="customer@example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([User(email="Customer@example.com")])


@pytest.mark.parametrize("email", [None, "", "   "])
def test_model_validation_rejects_missing_email_without_attribute_error(email):
    user = User(email=email)

    with pytest.raises(ValidationError) as exc_info:
        user.full_clean()

    assert "email" in exc_info.value.message_dict
