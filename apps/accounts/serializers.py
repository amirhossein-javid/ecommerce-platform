from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


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
