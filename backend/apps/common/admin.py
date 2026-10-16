from django import forms
from django.contrib import admin
from django.contrib.auth.forms import AuthenticationForm, UsernameField


class PersianAdminAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label="ایمیل",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="گذرواژه",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


admin.site.login_form = PersianAdminAuthenticationForm
