from rest_framework import serializers

from .models import PaymentAttempt


class PaymentInitiationRequestSerializer(serializers.Serializer):
    pass


class PaymentAttemptSerializer(serializers.ModelSerializer):
    payment_url = serializers.URLField(read_only=True, allow_null=True)

    class Meta:
        model = PaymentAttempt
        fields = (
            "id",
            "status",
            "amount",
            "currency",
            "payment_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PaymentVerificationRequestSerializer(serializers.Serializer):
    callback_data = serializers.JSONField()

    def validate_callback_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected a JSON object.")
        return value


class PaymentErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
