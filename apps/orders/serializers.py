from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Order, OrderItem


class CheckoutRequestSerializer(serializers.Serializer):
    address_id = serializers.IntegerField(min_value=1, required=False)


class CheckoutOrderItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=0,
        read_only=True,
    )
    line_total = serializers.DecimalField(
        max_digits=20,
        decimal_places=0,
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        )
        read_only_fields = fields


class CheckoutOrderSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    discount_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    shipping_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    grand_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    items = CheckoutOrderItemSerializer(many=True, read_only=True)
    payment_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "subtotal",
            "discount_total",
            "shipping_total",
            "grand_total",
            "shipping_title",
            "shipping_recipient_first_name",
            "shipping_recipient_last_name",
            "shipping_recipient_phone_number",
            "shipping_province",
            "shipping_city",
            "shipping_address",
            "shipping_postal_code",
            "items",
            "created_at",
            "payment_expires_at",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.DateTimeField())
    def get_payment_expires_at(self, obj):
        reservations = getattr(obj, "prefetched_inventory_reservations", ())
        if not reservations:
            return None
        return min(reservation.expires_at for reservation in reservations)


class CheckoutValidationErrorSerializer(serializers.Serializer):
    detail = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    address_id = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )


class CheckoutErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CustomerOrderListSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    discount_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    shipping_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    grand_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "subtotal",
            "discount_total",
            "shipping_total",
            "grand_total",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CustomerOrderItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=0,
        read_only=True,
    )
    line_total = serializers.DecimalField(
        max_digits=20,
        decimal_places=0,
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = (
            "product_name",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        )
        read_only_fields = fields


class CustomerOrderDetailSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    discount_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    shipping_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    grand_total = serializers.DecimalField(
        max_digits=22,
        decimal_places=0,
        read_only=True,
    )
    items = CustomerOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "subtotal",
            "discount_total",
            "shipping_total",
            "grand_total",
            "shipping_title",
            "shipping_recipient_first_name",
            "shipping_recipient_last_name",
            "shipping_recipient_phone_number",
            "shipping_province",
            "shipping_city",
            "shipping_address",
            "shipping_postal_code",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
