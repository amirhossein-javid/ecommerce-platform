import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.models import User


def test_admin_branding_is_persian_and_keeps_native_site():
    assert admin.site.site_header == "مدیریت فروشگاه نقش‌جهان"
    assert admin.site.site_title == "نقش‌جهان"
    assert admin.site.index_title == "مرکز مدیریت فروشگاه"


@pytest.mark.django_db
def test_admin_login_is_rtl_and_loads_local_theme(client):
    response = client.get(reverse("admin:login"))

    assert response.status_code == 200
    assert b'<html lang="fa" dir="rtl">' in response.content
    assert b"naghsh_admin/css/admin.css" in response.content
    assert "نقش‌جهان" in response.content.decode()
    assert "ایمیل" in response.content.decode()


@pytest.mark.django_db
def test_admin_index_keeps_permission_filtered_native_app_list(client):
    operator = User.objects.create_user("theme-operator@example.com", "password")
    operator.is_staff = True
    operator.save(update_fields=("is_staff",))
    client.force_login(operator)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200
    assert response.context["available_apps"] == []
    assert "فقط بخش‌هایی نمایش داده می‌شوند" in response.content.decode()
