import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.admin import CustomerProfileAdmin
from apps.accounts.models import CustomerProfile, User


def test_customer_profile_is_registered_with_custom_admin():
    assert isinstance(
        admin.site._registry[CustomerProfile],
        CustomerProfileAdmin,
    )


@pytest.mark.django_db
def test_superuser_can_open_customer_profile_admin(client):
    superuser = User.objects.create_superuser(
        "admin@example.com",
        "strong-password",
    )
    profile_user = User.objects.create_user("customer@example.com")
    CustomerProfile.objects.create(
        user=profile_user,
        first_name="Customer",
        phone_number="+14155552671",
    )
    client.force_login(superuser)

    response = client.get(reverse("admin:accounts_customerprofile_changelist"))

    assert response.status_code == 200
    assert b"customer@example.com" in response.content


@pytest.mark.django_db
def test_existing_profile_owner_is_readonly_in_admin(client):
    superuser = User.objects.create_superuser("admin@example.com", "password")
    first_user = User.objects.create_user("first@example.com")
    second_user = User.objects.create_user("second@example.com")
    profile = CustomerProfile.objects.create(user=first_user)
    client.force_login(superuser)

    response = client.post(
        reverse("admin:accounts_customerprofile_change", args=(profile.pk,)),
        {
            "user": second_user.pk,
            "first_name": "Updated",
            "last_name": "Customer",
            "phone_number": "",
            "_save": "Save",
        },
    )

    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.user == first_user
    assert profile.first_name == "Updated"
