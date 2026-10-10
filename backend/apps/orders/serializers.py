from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Order, OrderItem, OrderStatusHistory, Shipment


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


class OrderCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "refund_status",
            "cancelled_at",
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
            "items",
            "created_at",
            "updated_at",
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


class ManagementOrderFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status, required=False)
    search = serializers.CharField(max_length=255, required=False, trim_whitespace=True)


class ManagementShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = ("carrier", "tracking_number", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_carrier(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Carrier is required.")
        return value

    def validate_tracking_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Tracking number is required.")
        return value


class ManagementOrderHistorySerializer(serializers.ModelSerializer):
    actor_display_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = (
            "from_status",
            "to_status",
            "actor_type",
            "actor_display_name",
            "created_at",
        )
        read_only_fields = fields

    def get_actor_display_name(self, obj) -> str:
        if obj.actor_user_id is None:
            return ""
        return obj.actor_user.email


class ManagementOrderListSerializer(serializers.ModelSerializer):
    customer_display_name = serializers.SerializerMethodField()
    item_count = serializers.IntegerField(read_only=True)
    grand_total = serializers.DecimalField(
        max_digits=22, decimal_places=0, read_only=True
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "refund_status",
            "customer_display_name",
            "item_count",
            "grand_total",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_customer_display_name(self, obj) -> str:
        name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
        return name or obj.customer.user.email


class ManagementOrderDetailSerializer(ManagementOrderListSerializer):
    customer_email = serializers.EmailField(
        source="customer.user.email", read_only=True
    )
    subtotal = serializers.DecimalField(max_digits=22, decimal_places=0, read_only=True)
    discount_total = serializers.DecimalField(
        max_digits=22, decimal_places=0, read_only=True
    )
    shipping_total = serializers.DecimalField(
        max_digits=22, decimal_places=0, read_only=True
    )
    items = CheckoutOrderItemSerializer(many=True, read_only=True)
    shipment = ManagementShipmentSerializer(read_only=True)
    status_history = ManagementOrderHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ManagementOrderListSerializer.Meta.fields + (
            "customer_email",
            "subtotal",
            "discount_total",
            "shipping_total",
            "shipping_title",
            "shipping_recipient_first_name",
            "shipping_recipient_last_name",
            "shipping_recipient_phone_number",
            "shipping_province",
            "shipping_city",
            "shipping_address",
            "shipping_postal_code",
            "paid_at",
            "processing_at",
            "shipped_at",
            "delivered_at",
            "cancelled_at",
            "refund_resolved_at",
            "items",
            "shipment",
            "status_history",
        )
        read_only_fields = fields


class ManagementOrderTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
            Order.Status.CANCELLED,
        )
    )


class ManagementDashboardSummarySerializer(serializers.Serializer):
    order_count = serializers.IntegerField(min_value=0)
    successful_revenue = serializers.DecimalField(max_digits=24, decimal_places=0)
    pending_fulfillment_count = serializers.IntegerField(min_value=0)
    low_stock_product_count = serializers.IntegerField(min_value=0)
    low_stock_threshold = serializers.IntegerField(min_value=0)
