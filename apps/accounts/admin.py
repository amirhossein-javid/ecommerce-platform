from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import Address, CustomerProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    model = User

    list_display = ("email", "is_active", "is_staff", "is_superuser")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("email",)
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "first_name",
        "last_name",
        "phone_number",
        "updated_at",
    )
    search_fields = ("user__email", "first_name", "last_name", "phone_number")
    list_select_related = ("user",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user__email",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "customer_profile",
        "recipient_first_name",
        "recipient_last_name",
        "province",
        "city",
        "is_default",
        "updated_at",
    )
    list_filter = ("is_default",)
    search_fields = (
        "title",
        "recipient_first_name",
        "recipient_last_name",
        "recipient_phone_number",
        "postal_code",
        "customer_profile__user__email",
    )
    autocomplete_fields = ("customer_profile",)
    list_select_related = ("customer_profile", "customer_profile__user")
    readonly_fields = ("created_at", "updated_at")
