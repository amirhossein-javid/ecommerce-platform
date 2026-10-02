import pytest
from django.db import OperationalError
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_returns_ok_without_database_query(django_assert_num_queries):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer invalid-probe-credential")

    with django_assert_num_queries(0):
        response = client.get(reverse("common:health-check"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_check_returns_ready_when_database_is_available(
    django_assert_num_queries,
):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer invalid-probe-credential")

    with django_assert_num_queries(1):
        response = client.get(reverse("common:readiness-check"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ready"}


def test_readiness_check_hides_database_failure_details(monkeypatch):
    sensitive_error = "password=secret host=private-database.internal"

    def unavailable_cursor():
        raise OperationalError(sensitive_error)

    monkeypatch.setattr("apps.common.views.connection.cursor", unavailable_cursor)

    response = APIClient().get(reverse("common:readiness-check"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "unavailable"}
    assert sensitive_error.encode() not in response.content


@override_settings(
    SECURE_SSL_REDIRECT=True,
    SECURE_REDIRECT_EXEMPT=[r"^api/v1/health/$"],
)
def test_http_liveness_is_exempt_without_weakening_other_https_redirects():
    client = APIClient()

    liveness_response = client.get(reverse("common:health-check"))
    readiness_response = client.get(reverse("common:readiness-check"))

    assert liveness_response.status_code == status.HTTP_200_OK
    assert liveness_response.json() == {"status": "ok"}
    assert readiness_response.status_code == status.HTTP_301_MOVED_PERMANENTLY
    assert readiness_response["Location"].startswith("https://")
