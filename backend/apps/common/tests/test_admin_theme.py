from datetime import UTC, date, datetime

import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.models import User
from apps.common.admin_presentation import (
    format_admin_temporal,
    gregorian_to_jalali,
)
from apps.common.admin_site import NaghshAdminSite


def test_admin_branding_is_persian_and_keeps_native_site():
    assert isinstance(admin.site, NaghshAdminSite)
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


@pytest.mark.django_db
def test_admin_index_localizes_apps_and_models_without_changing_registry(client):
    operator = User.objects.create_superuser("theme-admin@example.com", "password")
    client.force_login(operator)

    response = client.get(reverse("admin:index"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "حساب‌ها و مشتریان" in content
    assert "سفارش‌ها و ارسال" in content
    assert "کاتالوگ و دیدگاه‌ها" in content
    assert "پروفایل‌های مشتریان" in content
    assert "دیدگاه‌های محصولات" in content
    assert 'class="colM naghsh-dashboard-shell"' in content
    assert 'class="naghsh-dashboard-layout"' in content
    assert 'class="naghsh-app-grid"' in content
    assert 'id="content-related"' not in content


@pytest.mark.django_db
def test_authenticated_admin_header_uses_explicit_responsive_structure(client):
    operator = User.objects.create_superuser("header-admin@example.com", "password")
    client.force_login(operator)

    response = client.get(reverse("admin:index"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'class="naghsh-header"' in content
    assert 'class="naghsh-header__inner"' in content
    assert 'class="naghsh-header__account"' in content
    assert 'aria-label="پیوندهای حساب مدیریت"' in content


def test_jalali_date_formatter_uses_persian_numerals():
    assert gregorian_to_jalali(2024, 3, 20) == (1403, 1, 1)
    assert format_admin_temporal(date(2024, 3, 20)) == "۱۴۰۳/۰۱/۰۱"


def test_admin_datetime_formatter_converts_to_tehran_before_jalali_date():
    before_midnight = datetime(2025, 3, 20, 20, 29, tzinfo=UTC)
    after_midnight = datetime(2025, 3, 20, 20, 31, tzinfo=UTC)

    assert format_admin_temporal(before_midnight) == "۱۴۰۳/۱۲/۳۰، ۲۳:۵۹"
    assert format_admin_temporal(after_midnight) == "۱۴۰۴/۰۱/۰۱، ۰۰:۰۱"


@pytest.mark.django_db
def test_admin_user_password_help_is_persian(client):
    operator = User.objects.create_superuser("form-admin@example.com", "password")
    client.force_login(operator)

    response = client.get(reverse("admin:accounts_user_change", args=(operator.pk,)))
    content = response.content.decode()

    assert response.status_code == 200
    assert "بازنشانی گذرواژه" in content
    assert "گذرواژه خام ذخیره نمی‌شود" in content
    assert "Raw passwords are not stored" not in content
