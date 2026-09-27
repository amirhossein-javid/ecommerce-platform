import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.admin import AddressAdmin
from apps.accounts.models import Address, CustomerProfile, User


def test_address_is_registered_with_custom_admin():
    assert isinstance(admin.site._registry[Address], AddressAdmin)


@pytest.mark.django_db
def test_superuser_can_open_address_admin(client):
    superuser = User.objects.create_superuser(
        "admin@example.com",
        "strong-password",
    )
    customer = User.objects.create_user("customer@example.com")
    profile = CustomerProfile.objects.create(user=customer)
    Address.objects.create(
        customer_profile=profile,
        title="Home",
        recipient_first_name="Ali",
        recipient_last_name="Ahmadi",
        recipient_phone_number="+989121234567",
        province="Tehran",
        city="Tehran",
        address="Azadi Street",
        postal_code="1234567890",
    )
    client.force_login(superuser)

    response = client.get(reverse("admin:accounts_address_changelist"))

    assert response.status_code == 200
    assert b"Home" in response.content
    assert b"customer@example.com" in response.content
