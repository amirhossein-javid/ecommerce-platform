from datetime import timedelta

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import User

ONE_AUTH_REQUEST_PER_MINUTE = {
    **settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "auth_login": "1/minute",
        "auth_refresh": "1/minute",
    },
}


class ProtectedTestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({"user_id": request.user.pk})


@pytest.fixture
def user(db):
    return User.objects.create_user(
        "customer@example.com",
        "strong-password",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_login_returns_access_and_refresh_tokens(api_client, user):
    response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "strong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert set(response.json()) == {"access", "refresh"}
    assert AccessToken(response.json()["access"])["user_id"] == str(user.pk)
    assert RefreshToken(response.json()["refresh"])["user_id"] == str(user.pk)


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=ONE_AUTH_REQUEST_PER_MINUTE)
def test_login_throttle_counts_failed_attempts(
    api_client, user, configure_throttle_rates
):
    configure_throttle_rates(auth_login="1/minute")
    first_response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "wrong-password"},
        format="json",
    )
    blocked_response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "strong-password"},
        format="json",
    )

    assert first_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert blocked_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
def test_login_accepts_email_regardless_of_case(api_client, user):
    response = api_client.post(
        reverse("accounts:login"),
        {"email": "Customer@EXAMPLE.COM", "password": "strong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_login_requires_email_instead_of_username(api_client, user):
    response = api_client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "strong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "customer@example.com", "password": "wrong-password"},
        {"email": "missing@example.com", "password": "strong-password"},
    ],
)
def test_login_rejects_invalid_credentials(api_client, user, credentials):
    response = api_client.post(
        reverse("accounts:login"),
        credentials,
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "access" not in response.json()
    assert "refresh" not in response.json()


@pytest.mark.django_db
def test_login_rejects_inactive_user(api_client, user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "strong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_access_token_authenticates_user(user):
    access = str(RefreshToken.for_user(user).access_token)
    request = APIRequestFactory().get(
        "/protected/",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )

    response = ProtectedTestView.as_view()(request)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"user_id": user.pk}


@pytest.mark.django_db
def test_refresh_token_cannot_be_used_as_access_token(user):
    refresh = str(RefreshToken.for_user(user))
    request = APIRequestFactory().get(
        "/protected/",
        HTTP_AUTHORIZATION=f"Bearer {refresh}",
    )

    response = ProtectedTestView.as_view()(request)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_access_token_is_rejected_by_refresh_endpoint(api_client, user):
    access = str(RefreshToken.for_user(user).access_token)

    response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": access},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "access" not in response.json()
    assert "refresh" not in response.json()


@pytest.mark.django_db
def test_refresh_rotates_token_and_blacklists_previous_refresh(api_client, user):
    original_refresh = str(RefreshToken.for_user(user))

    response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": original_refresh},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert set(response.json()) == {"access", "refresh"}
    assert response.json()["refresh"] != original_refresh
    assert BlacklistedToken.objects.count() == 1

    reused_response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": original_refresh},
        format="json",
    )

    assert reused_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_flush_expired_tokens_removes_only_expired_blacklist_records(user):
    expired_refresh = RefreshToken.for_user(user)
    valid_refresh = RefreshToken.for_user(user)
    expired_refresh.blacklist()
    valid_refresh.blacklist()
    expired_outstanding = OutstandingToken.objects.get(jti=expired_refresh["jti"])
    valid_outstanding = OutstandingToken.objects.get(jti=valid_refresh["jti"])
    OutstandingToken.objects.filter(pk=expired_outstanding.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    call_command("flushexpiredtokens")

    assert not OutstandingToken.objects.filter(pk=expired_outstanding.pk).exists()
    assert not BlacklistedToken.objects.filter(token_id=expired_outstanding.pk).exists()
    assert OutstandingToken.objects.filter(pk=valid_outstanding.pk).exists()
    assert BlacklistedToken.objects.filter(token_id=valid_outstanding.pk).exists()


@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=ONE_AUTH_REQUEST_PER_MINUTE)
def test_refresh_throttle_blocks_additional_token_rotation(
    api_client, user, configure_throttle_rates
):
    configure_throttle_rates(auth_refresh="1/minute")
    first_response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": str(RefreshToken.for_user(user))},
        format="json",
    )
    blocked_response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": first_response.json()["refresh"]},
        format="json",
    )

    assert first_response.status_code == status.HTTP_200_OK
    assert blocked_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert BlacklistedToken.objects.count() == 1


@pytest.mark.django_db
def test_rotated_refresh_token_can_be_used(api_client, user):
    original_refresh = str(RefreshToken.for_user(user))
    first_response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": original_refresh},
        format="json",
    )

    second_response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": first_response.json()["refresh"]},
        format="json",
    )

    assert second_response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_refresh_rejects_inactive_user(api_client, user):
    refresh = str(RefreshToken.for_user(user))
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": refresh},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_refresh_rejects_token_for_deleted_user_without_server_error(api_client, user):
    refresh = str(RefreshToken.for_user(user))
    user.delete()

    response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": refresh},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "access" not in response.json()
    assert "refresh" not in response.json()


@pytest.mark.django_db
def test_existing_access_token_rejects_user_deactivated_after_issuance(user):
    access = str(RefreshToken.for_user(user).access_token)
    user.is_active = False
    user.save(update_fields=["is_active"])
    request = APIRequestFactory().get(
        "/protected/",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )

    response = ProtectedTestView.as_view()(request)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_logout_blacklists_submitted_refresh_token(api_client, user):
    refresh = str(RefreshToken.for_user(user))

    response = api_client.post(
        reverse("accounts:logout"),
        {"refresh": refresh},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert BlacklistedToken.objects.count() == 1

    refresh_response = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": refresh},
        format="json",
    )

    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_logout_does_not_revoke_already_issued_access_token(api_client, user):
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    api_client.post(
        reverse("accounts:logout"),
        {"refresh": str(refresh)},
        format="json",
    )
    request = APIRequestFactory().get(
        "/protected/",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )

    response = ProtectedTestView.as_view()(request)

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_logout_rejects_access_token_in_refresh_field(api_client, user):
    access = str(RefreshToken.for_user(user).access_token)

    response = api_client.post(
        reverse("accounts:logout"),
        {"refresh": access},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.parametrize("payload", [{}, {"refresh": "not-a-token"}])
def test_logout_rejects_missing_or_invalid_refresh(api_client, payload):
    response = api_client.post(
        reverse("accounts:logout"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_logout_does_not_require_access_token(api_client, user):
    refresh = str(RefreshToken.for_user(user))

    response = api_client.post(
        reverse("accounts:logout"),
        {"refresh": refresh},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
