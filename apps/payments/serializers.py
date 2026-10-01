from rest_framework import serializers

from .models import PaymentAttempt


class PaymentInitiationRequestSerializer(serializers.Serializer):
    pass


class PaymentAttemptSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    payment_url = serializers.URLField(read_only=True, allow_null=True)
    payment_identifier = serializers.CharField(
        source="customer_payment_identifier",
        max_length=255,
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = PaymentAttempt
        fields = (
            "id",
            "status",
            "amount",
            "currency",
            "payment_url",
            "payment_identifier",
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


class BalePreCheckoutQuerySerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255)
    currency = serializers.CharField(max_length=3)
    total_amount = serializers.IntegerField(min_value=0)
    invoice_payload = serializers.CharField(max_length=128)


class BaleSuccessfulPaymentSerializer(serializers.Serializer):
    currency = serializers.CharField(max_length=3)
    total_amount = serializers.IntegerField(min_value=0)
    invoice_payload = serializers.CharField(max_length=128)
    telegram_payment_charge_id = serializers.CharField(max_length=255)
    provider_payment_charge_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=False,
    )


class BaleMessageSerializer(serializers.Serializer):
    successful_payment = BaleSuccessfulPaymentSerializer(required=False)


class BaleUpdateSerializer(serializers.Serializer):
    update_id = serializers.IntegerField(
        min_value=0, max_value=9_223_372_036_854_775_807
    )
    pre_checkout_query = BalePreCheckoutQuerySerializer(required=False)
    message = BaleMessageSerializer(required=False)

    def validate(self, attrs):
        has_pre_checkout = "pre_checkout_query" in attrs
        has_message = "message" in attrs
        if has_pre_checkout and has_message:
            raise serializers.ValidationError("Expected one payment update type.")
        return attrs


class BaleWebhookResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
