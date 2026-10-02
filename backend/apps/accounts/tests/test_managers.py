import pytest
from django.contrib.auth import authenticate

from apps.accounts.models import User


@pytest.mark.django_db
def test_create_user_normalizes_email_and_hashes_password():
    user = User.objects.create_user("  Customer@EXAMPLE.COM ", "strong-password")

    assert user.email == "customer@example.com"
    assert user.password != "strong-password"
    assert user.check_password("strong-password")
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False


@pytest.mark.django_db
def test_create_user_without_password_sets_unusable_password():
    user = User.objects.create_user("customer@example.com")

    assert user.has_usable_password() is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "login_email",
    ["customer@example.com", "Customer@EXAMPLE.COM"],
)
def test_authentication_accepts_email_regardless_of_case(login_email):
    user = User.objects.create_user("customer@example.com", "strong-password")

    authenticated_user = authenticate(
        email=login_email,
        password="strong-password",
    )

    assert authenticated_user == user


@pytest.mark.django_db
@pytest.mark.parametrize("email", [None, "", "   "])
def test_create_user_requires_email(email):
    with pytest.raises(ValueError, match="email address must be provided"):
        User.objects.create_user(email, "strong-password")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "privileged_field",
    ["is_staff", "is_superuser"],
)
def test_create_user_rejects_privileged_flags(privileged_field):
    with pytest.raises(ValueError):
        User.objects.create_user(
            "customer@example.com",
            "strong-password",
            **{privileged_field: True},
        )


@pytest.mark.django_db
def test_create_superuser_sets_required_flags():
    user = User.objects.create_superuser("Admin@EXAMPLE.COM", "strong-password")

    assert user.email == "admin@example.com"
    assert user.check_password("strong-password")
    assert user.is_active is True
    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("is_staff", False),
        ("is_superuser", False),
        ("is_active", False),
    ],
)
def test_create_superuser_rejects_invalid_flags(field, value):
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            "admin@example.com",
            "strong-password",
            **{field: value},
        )


@pytest.mark.django_db
@pytest.mark.parametrize("password", [None, ""])
def test_create_superuser_requires_password(password):
    with pytest.raises(ValueError, match="must have a password"):
        User.objects.create_superuser("admin@example.com", password)
