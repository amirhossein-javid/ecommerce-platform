from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import IntegrityError, connections, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Address, CustomerProfile, User

ADDRESS_DATA = {
    "title": "Home",
    "recipient_first_name": "Ali",
    "recipient_last_name": "Ahmadi",
    "recipient_phone_number": "+989121234567",
    "province": "Tehran",
    "city": "Tehran",
    "address": "Example street, building 10",
    "postal_code": "1234567890",
}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    user = User.objects.create_user("customer@example.com", "strong-password")
    profile = CustomerProfile.objects.create(
        user=user,
        first_name="Ali",
        last_name="Ahmadi",
        phone_number="+989121234567",
    )
    return user, profile


def authenticate(client, user):
    access_token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")


def create_address(profile, **overrides):
    data = {**ADDRESS_DATA, **overrides}
    return Address.objects.create(customer_profile=profile, **data)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url_name", "kwargs", "payload"),
    [
        ("get", "account:profile", {}, None),
        ("patch", "account:profile", {}, {"first_name": "Reza"}),
        ("get", "account:address-list", {}, None),
        ("post", "account:address-list", {}, ADDRESS_DATA),
        ("get", "account:address-detail", {"pk": 1}, None),
        ("patch", "account:address-detail", {"pk": 1}, {"title": "Work"}),
        ("delete", "account:address-detail", {"pk": 1}, None),
        ("post", "account:address-set-default", {"pk": 1}, None),
    ],
)
def test_customer_account_endpoints_require_authentication(
    api_client,
    method,
    url_name,
    kwargs,
    payload,
):
    response = getattr(api_client, method)(
        reverse(url_name, kwargs=kwargs),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_profile_get_returns_current_customer_data(api_client, customer):
    user, profile = customer
    authenticate(api_client, user)

    response = api_client.get(reverse("account:profile"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": profile.pk,
        "email": user.email,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "phone_number": profile.phone_number,
        "created_at": response.json()["created_at"],
        "updated_at": response.json()["updated_at"],
    }


@pytest.mark.django_db
def test_profile_patch_updates_only_current_profile(api_client, customer):
    user, profile = customer
    other_user = User.objects.create_user("other@example.com", "strong-password")
    other_profile = CustomerProfile.objects.create(
        user=other_user,
        first_name="Other",
    )
    authenticate(api_client, user)

    response = api_client.patch(
        reverse("account:profile"),
        {
            "first_name": "Reza",
            "last_name": "Karimi",
            "phone_number": "+989351234567",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    profile.refresh_from_db()
    other_profile.refresh_from_db()
    assert profile.first_name == "Reza"
    assert profile.last_name == "Karimi"
    assert profile.phone_number == "+989351234567"
    assert other_profile.first_name == "Other"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "email",
        "password",
        "user",
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
        "user_permissions",
    ],
)
def test_profile_rejects_account_and_privilege_fields(api_client, customer, field):
    user, profile = customer
    authenticate(api_client, user)

    response = api_client.patch(
        reverse("account:profile"),
        {field: "attacker-controlled"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field in response.json()
    user.refresh_from_db()
    profile.refresh_from_db()
    assert user.email == "customer@example.com"
    assert user.is_staff is False
    assert user.is_superuser is False


@pytest.mark.django_db
def test_profile_patch_reuses_phone_validator(api_client, customer):
    user, profile = customer
    authenticate(api_client, user)

    response = api_client.patch(
        reverse("account:profile"),
        {"phone_number": "09121234567"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "phone_number" in response.json()
    profile.refresh_from_db()
    assert profile.phone_number == "+989121234567"


@pytest.mark.django_db
def test_address_crud_is_scoped_to_current_customer(api_client, customer):
    user, profile = customer
    other_user = User.objects.create_user("other@example.com", "strong-password")
    other_profile = CustomerProfile.objects.create(user=other_user)
    other_address = create_address(other_profile, is_default=True)
    authenticate(api_client, user)

    create_response = api_client.post(
        reverse("account:address-list"),
        ADDRESS_DATA,
        format="json",
    )
    address_id = create_response.json()["id"]
    list_response = api_client.get(reverse("account:address-list"))
    retrieve_response = api_client.get(
        reverse("account:address-detail", kwargs={"pk": address_id})
    )
    update_response = api_client.patch(
        reverse("account:address-detail", kwargs={"pk": address_id}),
        {"title": "Parents"},
        format="json",
    )
    delete_response = api_client.delete(
        reverse("account:address-detail", kwargs={"pk": address_id})
    )

    assert create_response.status_code == status.HTTP_201_CREATED
    assert create_response.json()["is_default"] is True
    assert list_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in list_response.json()] == [address_id]
    assert other_address.pk not in [item["id"] for item in list_response.json()]
    assert retrieve_response.status_code == status.HTTP_200_OK
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["title"] == "Parents"
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert Address.objects.filter(customer_profile=profile).exists() is False


@pytest.mark.django_db
def test_subsequent_address_does_not_replace_existing_default(api_client, customer):
    user, profile = customer
    authenticate(api_client, user)

    first_response = api_client.post(
        reverse("account:address-list"),
        ADDRESS_DATA,
        format="json",
    )
    second_response = api_client.post(
        reverse("account:address-list"),
        {**ADDRESS_DATA, "title": "Work"},
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert first_response.json()["is_default"] is True
    assert second_response.json()["is_default"] is False
    assert profile.addresses.get(is_default=True).pk == first_response.json()["id"]


@pytest.mark.django_db
def test_customer_can_switch_default_address(api_client, customer):
    user, profile = customer
    first_address = create_address(profile, is_default=True)
    second_address = create_address(profile, title="Work")
    authenticate(api_client, user)

    response = api_client.post(
        reverse("account:address-set-default", kwargs={"pk": second_address.pk})
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == second_address.pk
    assert response.json()["is_default"] is True
    first_address.refresh_from_db()
    second_address.refresh_from_db()
    assert first_address.is_default is False
    assert second_address.is_default is True
    assert profile.addresses.filter(is_default=True).count() == 1


@pytest.mark.django_db
def test_deleting_default_address_does_not_promote_another(api_client, customer):
    user, profile = customer
    default_address = create_address(profile, is_default=True)
    other_address = create_address(profile, title="Work")
    authenticate(api_client, user)

    response = api_client.delete(
        reverse("account:address-detail", kwargs={"pk": default_address.pk})
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    other_address.refresh_from_db()
    assert other_address.is_default is False
    assert profile.addresses.filter(is_default=True).exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url_name"),
    [
        ("get", "account:address-detail"),
        ("patch", "account:address-detail"),
        ("delete", "account:address-detail"),
        ("post", "account:address-set-default"),
    ],
)
def test_cross_customer_address_access_returns_not_found(
    api_client,
    customer,
    method,
    url_name,
):
    user, _ = customer
    other_user = User.objects.create_user("other@example.com", "strong-password")
    other_profile = CustomerProfile.objects.create(user=other_user)
    other_address = create_address(other_profile, is_default=True)
    authenticate(api_client, user)

    response = getattr(api_client, method)(
        reverse(url_name, kwargs={"pk": other_address.pk}),
        {"title": "Stolen"} if method == "patch" else None,
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    other_address.refresh_from_db()
    assert other_address.title == ADDRESS_DATA["title"]
    assert other_address.is_default is True


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["customer_profile", "is_default"])
def test_address_create_rejects_ownership_and_default_injection(
    api_client,
    customer,
    field,
):
    user, profile = customer
    other_user = User.objects.create_user("other@example.com", "strong-password")
    other_profile = CustomerProfile.objects.create(user=other_user)
    injected_value = other_profile.pk if field == "customer_profile" else True
    authenticate(api_client, user)

    response = api_client.post(
        reverse("account:address-list"),
        {**ADDRESS_DATA, field: injected_value},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field in response.json()
    assert profile.addresses.exists() is False
    assert other_profile.addresses.exists() is False


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["customer_profile", "is_default"])
def test_address_update_rejects_ownership_and_default_injection(
    api_client,
    customer,
    field,
):
    user, profile = customer
    address = create_address(profile, is_default=True)
    other_user = User.objects.create_user("other@example.com", "strong-password")
    other_profile = CustomerProfile.objects.create(user=other_user)
    authenticate(api_client, user)

    injected_value = other_profile.pk if field == "customer_profile" else False
    response = api_client.patch(
        reverse("account:address-detail", kwargs={"pk": address.pk}),
        {field: injected_value},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    address.refresh_from_db()
    assert address.customer_profile_id == profile.pk
    assert address.is_default is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("recipient_phone_number", "09121234567"),
        ("postal_code", "12345"),
        ("address", "a" * 501),
        ("city", ""),
    ],
)
def test_address_create_reuses_model_validation(
    api_client,
    customer,
    field,
    value,
):
    user, profile = customer
    authenticate(api_client, user)

    response = api_client.post(
        reverse("account:address-list"),
        {**ADDRESS_DATA, field: value},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field in response.json()
    assert profile.addresses.exists() is False


@pytest.mark.django_db
def test_database_constraint_remains_final_default_invariant(customer):
    _, profile = customer
    create_address(profile, is_default=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        create_address(profile, title="Work", is_default=True)

    assert profile.addresses.filter(is_default=True).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_first_address_creation_produces_one_default():
    user = User.objects.create_user("concurrent@example.com", "strong-password")
    profile = CustomerProfile.objects.create(user=user)
    access_tokens = [
        str(RefreshToken.for_user(user).access_token),
        str(RefreshToken.for_user(user).access_token),
    ]
    barrier = Barrier(2)

    def create_from_thread(title, access_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        barrier.wait()
        try:
            return client.post(
                reverse("account:address-list"),
                {**ADDRESS_DATA, "title": title},
                format="json",
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(create_from_thread, title, token)
            for title, token in zip(("Home", "Work"), access_tokens, strict=True)
        ]
        response_statuses = [future.result() for future in futures]

    assert response_statuses == [status.HTTP_201_CREATED, status.HTTP_201_CREATED]
    assert profile.addresses.count() == 2
    assert profile.addresses.filter(is_default=True).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_default_switches_preserve_single_default():
    user = User.objects.create_user("concurrent@example.com", "strong-password")
    profile = CustomerProfile.objects.create(user=user)
    original_default = create_address(profile, is_default=True)
    first_target = create_address(profile, title="Work")
    second_target = create_address(profile, title="Parents")
    access_tokens = [
        str(RefreshToken.for_user(user).access_token),
        str(RefreshToken.for_user(user).access_token),
    ]
    barrier = Barrier(2)

    def switch_from_thread(address_id, access_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        barrier.wait()
        try:
            return client.post(
                reverse(
                    "account:address-set-default",
                    kwargs={"pk": address_id},
                )
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(switch_from_thread, address.pk, token)
            for address, token in zip(
                (first_target, second_target),
                access_tokens,
                strict=True,
            )
        ]
        response_statuses = [future.result() for future in futures]

    original_default.refresh_from_db()
    assert response_statuses == [status.HTTP_200_OK, status.HTTP_200_OK]
    assert original_default.is_default is False
    assert profile.addresses.filter(is_default=True).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url_name", "kwargs", "payload"),
    [
        ("get", "account:profile", {}, None),
        ("get", "account:address-list", {}, None),
        ("post", "account:address-list", {}, ADDRESS_DATA),
        ("get", "account:address-detail", {"pk": 1}, None),
        ("post", "account:address-set-default", {"pk": 1}, None),
    ],
)
def test_authenticated_user_without_profile_receives_safe_not_found(
    api_client,
    db,
    method,
    url_name,
    kwargs,
    payload,
):
    user = User.objects.create_user("profileless@example.com", "strong-password")
    authenticate(api_client, user)

    response = getattr(api_client, method)(
        reverse(url_name, kwargs=kwargs),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Customer profile not found."}
