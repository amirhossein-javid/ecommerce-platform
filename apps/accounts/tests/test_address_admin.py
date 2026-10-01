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


@pytest.mark.django_db
def test_existing_address_owner_is_readonly_in_admin(client):
    superuser = User.objects.create_superuser("admin@example.com", "password")
    first_profile = CustomerProfile.objects.create(
        user=User.objects.create_user("first@example.com")
    )
    second_profile = CustomerProfile.objects.create(
        user=User.objects.create_user("second@example.com")
    )
    address = Address.objects.create(
        customer_profile=first_profile,
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

    response = client.post(
        reverse("admin:accounts_address_change", args=(address.pk,)),
        {
            "customer_profile": second_profile.pk,
            "title": "Updated",
            "recipient_first_name": address.recipient_first_name,
            "recipient_last_name": address.recipient_last_name,
            "recipient_phone_number": address.recipient_phone_number,
            "province": address.province,
            "city": address.city,
            "address": address.address,
            "postal_code": address.postal_code,
            "is_default": "",
            "_save": "Save",
        },
    )

    assert response.status_code == 302
    address.refresh_from_db()
    assert address.customer_profile == first_profile
    assert address.title == "Updated"
