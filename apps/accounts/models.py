from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .managers import UserManager
from .validators import validate_e164_phone_number, validate_iran_postal_code


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            )
        ]

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def save(self, *args, **kwargs):
        if self.email is not None:
            self.email = self.__class__.objects.normalize_email(self.email)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(
        max_length=16,
        blank=True,
        validators=[validate_e164_phone_number],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customer profile for {self.user}"


class Address(models.Model):
    customer_profile = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    title = models.CharField(max_length=50, blank=True)
    recipient_first_name = models.CharField(max_length=150)
    recipient_last_name = models.CharField(max_length=150)
    recipient_phone_number = models.CharField(
        max_length=16,
        validators=[validate_e164_phone_number],
    )
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.TextField(max_length=500)
    postal_code = models.CharField(
        max_length=10,
        validators=[validate_iran_postal_code],
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("customer_profile",),
                condition=models.Q(is_default=True),
                name="accounts_unique_default_address_per_profile",
            )
        ]

    def __str__(self):
        return self.title or f"Address for {self.customer_profile}"
