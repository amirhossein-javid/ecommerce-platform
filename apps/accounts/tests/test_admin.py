import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.admin import UserAdmin
from apps.accounts.models import User


def test_user_is_registered_with_custom_admin():
    assert isinstance(admin.site._registry[User], UserAdmin)


@pytest.mark.django_db
def test_superuser_can_open_user_admin_pages(client):
    superuser = User.objects.create_superuser(
        "admin@example.com",
        "strong-password",
    )
    client.force_login(superuser)

    changelist_response = client.get(reverse("admin:accounts_user_changelist"))
    add_response = client.get(reverse("admin:accounts_user_add"))

    assert changelist_response.status_code == 200
    assert add_response.status_code == 200
    assert b'name="username"' not in add_response.content
    assert b'name="email"' in add_response.content
    assert b'name="is_active"' not in add_response.content
    assert b'name="is_staff"' not in add_response.content
    assert b'name="is_superuser"' not in add_response.content
    assert b'name="groups"' not in add_response.content
    assert b'name="user_permissions"' not in add_response.content


@pytest.mark.django_db
def test_admin_add_form_creates_user_with_normalized_email(client):
    superuser = User.objects.create_superuser(
        "admin@example.com",
        "strong-password",
    )
    client.force_login(superuser)

    response = client.post(
        reverse("admin:accounts_user_add"),
        {
            "email": "Customer@EXAMPLE.COM",
            "password1": "a-secure-admin-password",
            "password2": "a-secure-admin-password",
            "is_active": "on",
        },
    )

    assert response.status_code == 302
    user = User.objects.get(email="customer@example.com")
    assert user.check_password("a-secure-admin-password")


@pytest.mark.django_db
def test_staff_with_only_add_user_permission_cannot_create_privileged_user(client):
    staff_user = User.objects.create_user(
        "staff@example.com",
        "strong-password",
    )
    staff_user.is_staff = True
    staff_user.save(update_fields=["is_staff"])
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="accounts",
            codename="add_user",
        )
    )
    client.force_login(staff_user)

    add_url = reverse("admin:accounts_user_add")
    add_response = client.get(add_url)

    assert add_response.status_code == 403

    post_response = client.post(
        add_url,
        {
            "email": "new-admin@example.com",
            "password1": "a-secure-admin-password",
            "password2": "a-secure-admin-password",
            "is_active": "on",
            "is_staff": "on",
            "is_superuser": "on",
            "groups": [staff_user.pk],
            "user_permissions": [staff_user.pk],
        },
    )

    assert post_response.status_code == 403
    assert User.objects.filter(email="new-admin@example.com").exists() is False


@pytest.mark.django_db
def test_privilege_fields_are_ignored_when_authorized_staff_adds_user(client):
    staff_user = User.objects.create_user(
        "staff@example.com",
        "strong-password",
    )
    staff_user.is_staff = True
    staff_user.save(update_fields=["is_staff"])
    staff_user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="accounts",
            codename__in=["add_user", "change_user"],
        )
    )
    client.force_login(staff_user)

    add_url = reverse("admin:accounts_user_add")
    add_response = client.get(add_url)

    assert add_response.status_code == 200
    assert b'name="is_active"' not in add_response.content
    assert b'name="is_staff"' not in add_response.content
    assert b'name="is_superuser"' not in add_response.content
    assert b'name="groups"' not in add_response.content
    assert b'name="user_permissions"' not in add_response.content

    post_response = client.post(
        add_url,
        {
            "email": "new-admin@example.com",
            "password1": "a-secure-admin-password",
            "password2": "a-secure-admin-password",
            "is_active": "on",
            "is_staff": "on",
            "is_superuser": "on",
            "groups": [staff_user.pk],
            "user_permissions": [staff_user.pk],
        },
    )

    assert post_response.status_code == 302
    created_user = User.objects.get(email="new-admin@example.com")
    assert created_user.is_active is True
    assert created_user.is_staff is False
    assert created_user.is_superuser is False
    assert created_user.groups.exists() is False
    assert created_user.user_permissions.exists() is False
