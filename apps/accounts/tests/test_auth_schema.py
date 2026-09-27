import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_schema_documents_authentication_endpoints_and_bearer_scheme():
    response = APIClient().get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert "/api/v1/auth/register/" in schema["paths"]
    assert "/api/v1/auth/login/" in schema["paths"]
    assert "/api/v1/auth/token/refresh/" in schema["paths"]
    assert "/api/v1/auth/logout/" in schema["paths"]
    customer_paths = (
        "/api/v1/account/profile/",
        "/api/v1/account/addresses/",
        "/api/v1/account/addresses/{id}/",
        "/api/v1/account/addresses/{id}/set-default/",
    )
    for path in customer_paths:
        assert path in schema["paths"]
        assert all(
            operation.get("security")
            for operation in schema["paths"][path].values()
            if isinstance(operation, dict) and "responses" in operation
        )
    assert "/api/v1/auth/profile/" not in schema["paths"]
    assert "/api/v1/auth/addresses/" not in schema["paths"]
    assert any(
        security_scheme.get("type") == "http"
        and security_scheme.get("scheme") == "bearer"
        for security_scheme in schema["components"]["securitySchemes"].values()
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/profile/",
        "/api/v1/auth/addresses/",
        "/api/v1/auth/addresses/1/",
        "/api/v1/auth/addresses/1/set-default/",
    ],
)
def test_old_customer_account_routes_are_not_exposed(path):
    response = APIClient().get(path)

    assert response.status_code == status.HTTP_404_NOT_FOUND
