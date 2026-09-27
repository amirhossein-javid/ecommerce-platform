import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_schema_documents_authentication_endpoints_and_bearer_scheme():
    response = APIClient().get(reverse("schema"), {"format": "json"})

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert "/api/v1/auth/login/" in schema["paths"]
    assert "/api/v1/auth/token/refresh/" in schema["paths"]
    assert "/api/v1/auth/logout/" in schema["paths"]
    assert any(
        security_scheme.get("type") == "http"
        and security_scheme.get("scheme") == "bearer"
        for security_scheme in schema["components"]["securitySchemes"].values()
    )
