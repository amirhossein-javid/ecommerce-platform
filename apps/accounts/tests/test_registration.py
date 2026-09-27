from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.test import APIClient

from apps.accounts.models import Address, CustomerProfile, User
from apps.accounts.serializers import CustomerRegistrationSerializer

VALID_REGISTRATION_DATA = {
    "email": "Customer@EXAMPLE.COM",
    "password": "a-secure-registration-password",
    "first_name": "Ali",
    "last_name": "Ahmadi",
    "phone_number": "+989121234567",
}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_registration_creates_user_and_customer_profile_atomically(api_client):
    response = api_client.post(
        reverse("accounts:register"),
        VALID_REGISTRATION_DATA,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"detail": "Registration successful. Please log in."}
    user = User.objects.get(email="customer@example.com")
    profile = user.customer_profile
    assert user.password != VALID_REGISTRATION_DATA["password"]
    assert user.check_password(VALID_REGISTRATION_DATA["password"])
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.groups.exists() is False
    assert user.user_permissions.exists() is False
    assert profile.first_name == VALID_REGISTRATION_DATA["first_name"]
    assert profile.last_name == VALID_REGISTRATION_DATA["last_name"]
    assert profile.phone_number == VALID_REGISTRATION_DATA["phone_number"]
    assert Address.objects.filter(customer_profile=profile).exists() is False
    assert "access" not in response.json()
    assert "refresh" not in response.json()


@pytest.mark.django_db
def test_registered_customer_can_log_in_separately(api_client):
    api_client.post(
        reverse("accounts:register"),
        VALID_REGISTRATION_DATA,
        format="json",
    )

    response = api_client.post(
        reverse("accounts:login"),
        {
            "email": "customer@example.com",
            "password": VALID_REGISTRATION_DATA["password"],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert set(response.json()) == {"access", "refresh"}


@pytest.mark.django_db
@pytest.mark.parametrize("email", ["customer@example.com", "Customer@EXAMPLE.COM"])
def test_registration_rejects_duplicate_email_with_generic_error(api_client, email):
    User.objects.create_user(
        "customer@example.com",
        VALID_REGISTRATION_DATA["password"],
    )
    payload = {**VALID_REGISTRATION_DATA, "email": email}

    response = api_client.post(
        reverse("accounts:register"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"email": ["Unable to register with this email address."]}
    assert User.objects.count() == 1
    assert CustomerProfile.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("first_name", ""),
        ("last_name", ""),
        ("phone_number", "09121234567"),
        ("phone_number", " +989121234567"),
    ],
)
def test_registration_rejects_invalid_profile_input_without_creating_user(
    api_client,
    field,
    value,
):
    payload = {**VALID_REGISTRATION_DATA, field: value}

    response = api_client.post(
        reverse("accounts:register"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field in response.json()
    assert User.objects.exists() is False
    assert CustomerProfile.objects.exists() is False


@pytest.mark.django_db
def test_registration_rejects_email_longer_than_user_model_limit(api_client):
    email_field = User._meta.get_field("email")
    local_part = "a" * (email_field.max_length - len("@example.com") + 1)
    payload = {**VALID_REGISTRATION_DATA, "email": f"{local_part}@example.com"}

    response = api_client.post(
        reverse("accounts:register"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.json()
    assert User.objects.exists() is False
    assert CustomerProfile.objects.exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "missing_field",
    ["email", "password", "first_name", "last_name", "phone_number"],
)
def test_registration_requires_all_fields(api_client, missing_field):
    payload = {
        key: value
        for key, value in VALID_REGISTRATION_DATA.items()
        if key != missing_field
    }

    response = api_client.post(
        reverse("accounts:register"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert missing_field in response.json()
    assert User.objects.exists() is False


@pytest.mark.django_db
def test_registration_uses_existing_password_validators(api_client):
    payload = {**VALID_REGISTRATION_DATA, "password": "12345678"}

    response = api_client.post(
        reverse("accounts:register"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.json()
    assert User.objects.exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "forbidden_field",
    ["is_staff", "is_superuser", "is_active", "groups", "user_permissions"],
)
def test_registration_rejects_privilege_fields(api_client, forbidden_field):
    payload = {**VALID_REGISTRATION_DATA, forbidden_field: True}

    response = api_client.post(
        reverse("accounts:register"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert forbidden_field in response.json()
    assert User.objects.exists() is False
    assert CustomerProfile.objects.exists() is False


@pytest.mark.django_db
def test_registration_rejects_non_object_payload(api_client):
    response = api_client.post(
        reverse("accounts:register"),
        [{"email": "customer@example.com"}],
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.exists() is False


@pytest.mark.django_db
def test_profile_creation_failure_rolls_back_user():
    serializer = CustomerRegistrationSerializer(data=VALID_REGISTRATION_DATA)
    assert serializer.is_valid(), serializer.errors

    with (
        patch.object(
            CustomerProfile.objects,
            "create",
            side_effect=RuntimeError("profile creation failed"),
        ),
        pytest.raises(RuntimeError, match="profile creation failed"),
    ):
        serializer.save()

    assert User.objects.exists() is False
    assert CustomerProfile.objects.exists() is False


@pytest.mark.django_db
def test_database_email_conflict_is_returned_as_validation_error():
    serializer = CustomerRegistrationSerializer(data=VALID_REGISTRATION_DATA)
    assert serializer.is_valid(), serializer.errors
    User.objects.create_user(
        "customer@example.com",
        VALID_REGISTRATION_DATA["password"],
    )

    with pytest.raises(serializers.ValidationError) as exc_info:
        serializer.save()

    assert exc_info.value.detail == {
        "email": ["Unable to register with this email address."]
    }
    assert User.objects.count() == 1
    assert CustomerProfile.objects.exists() is False


@pytest.mark.django_db
def test_duplicate_phone_numbers_are_allowed_during_registration(api_client):
    first_response = api_client.post(
        reverse("accounts:register"),
        VALID_REGISTRATION_DATA,
        format="json",
    )
    second_payload = {
        **VALID_REGISTRATION_DATA,
        "email": "second@example.com",
    }
    second_response = api_client.post(
        reverse("accounts:register"),
        second_payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert (
        CustomerProfile.objects.filter(
            phone_number=VALID_REGISTRATION_DATA["phone_number"]
        ).count()
        == 2
    )
