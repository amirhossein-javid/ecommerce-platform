from django.contrib.auth.forms import (
    ReadOnlyPasswordHashField,
    ReadOnlyPasswordHashWidget,
    UserChangeForm,
    UserCreationForm,
)
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)


class PersianReadOnlyPasswordHashWidget(ReadOnlyPasswordHashWidget):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        has_usable_password = value and not value.startswith(UNUSABLE_PASSWORD_PREFIX)
        context["button_label"] = (
            "بازنشانی گذرواژه" if has_usable_password else "تنظیم گذرواژه"
        )
        return context


class AdminUserChangeForm(UserChangeForm):
    password = ReadOnlyPasswordHashField(
        label="گذرواژه",
        help_text=(
            "گذرواژه خام ذخیره نمی‌شود؛ بنابراین امکان مشاهدهٔ گذرواژه کاربر وجود ندارد."
        ),
        widget=PersianReadOnlyPasswordHashWidget,
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("email",)
