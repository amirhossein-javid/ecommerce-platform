from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_health_check_returns_ok():
    response = APIClient().get(reverse("common:health-check"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
