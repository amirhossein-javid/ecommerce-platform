from collections.abc import Mapping

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Address, CustomerProfile, User


class RejectInputFieldsMixin:
    forbidden_fields = frozenset()

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            forbidden = self.forbidden_fields.intersection(data)
            if forbidden:
                raise serializers.ValidationError(
                    {field: "This field is not allowed." for field in sorted(forbidden)}
                )
        return super().to_internal_value(data)


class CustomerRegistrationSerializer(
    RejectInputFieldsMixin,
    serializers.ModelSerializer,
):
    email = serializers.EmailField(
        max_length=User._meta.get_field("email").max_length,
        write_only=True,
    )
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "email_unavailable": "Unable to register with this email address.",
    }
    forbidden_fields = frozenset(
        {
            "is_staff",
            "is_superuser",
            "is_active",
            "groups",
            "user_permissions",
        }
    )

    class Meta:
        model = CustomerProfile
        fields = ("email", "password", "first_name", "last_name", "phone_number")
        extra_kwargs = {
            "first_name": {"allow_blank": False, "required": True},
            "last_name": {"allow_blank": False, "required": True},
            "phone_number": {
                "allow_blank": False,
                "required": True,
                "trim_whitespace": False,
            },
        }

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email=email).exists():
            self.fail("email_unavailable")
        return email

    def validate(self, attrs):
        candidate_user = User(email=attrs["email"])
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"password": exc.messages},
            ) from exc
        return attrs

    def create(self, validated_data):
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        with transaction.atomic():
            try:
                with transaction.atomic():
                    user = User.objects.create_user(email=email, password=password)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"email": [self.error_messages["email_unavailable"]]}
                ) from exc
            return CustomerProfile.objects.create(user=user, **validated_data)


class CustomerProfileSerializer(RejectInputFieldsMixin, serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    forbidden_fields = frozenset(
        {
            "email",
            "password",
            "user",
            "is_staff",
            "is_superuser",
            "is_active",
            "groups",
            "user_permissions",
        }
    )

    class Meta:
        model = CustomerProfile
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "email", "created_at", "updated_at")


class AddressSerializer(RejectInputFieldsMixin, serializers.ModelSerializer):
    forbidden_fields = frozenset({"customer_profile", "is_default"})

    class Meta:
        model = Address
        fields = (
            "id",
            "title",
            "recipient_first_name",
            "recipient_last_name",
            "recipient_phone_number",
            "province",
            "city",
            "address",
            "postal_code",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_default", "created_at", "updated_at")


class RegistrationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
            token.blacklist()
        except TokenError as exc:
            raise serializers.ValidationError(
                "Invalid or expired refresh token.",
                code="invalid_token",
            ) from exc
        return value
