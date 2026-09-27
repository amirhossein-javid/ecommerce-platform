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
