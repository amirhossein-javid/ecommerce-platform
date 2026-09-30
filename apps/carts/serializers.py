from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.products.models import Product
from apps.products.serializers import ProductImageSerializer

from .models import CartItem


class CartProductSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("slug", "name", "price", "primary_image")
        read_only_fields = fields

    @extend_schema_field(ProductImageSerializer(allow_null=True))
    def get_primary_image(self, obj):
        images = getattr(obj, "prefetched_primary_images", ())
        if not images:
            return None
        return ProductImageSerializer(images[0], context=self.context).data


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)
    line_total = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    availability_reason = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "quantity",
            "line_total",
            "is_available",
            "availability_reason",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.DecimalField(max_digits=40, decimal_places=2))
    def get_line_total(self, obj):
        return format(obj.product.price * obj.quantity, ".2f")

    @extend_schema_field(serializers.BooleanField())
    def get_is_available(self, obj):
        return self._availability_reason(obj) is None

    @extend_schema_field(
        serializers.ChoiceField(
            choices=("unavailable", "insufficient_stock"),
            allow_null=True,
        )
    )
    def get_availability_reason(self, obj):
        return self._availability_reason(obj)

    @staticmethod
    def _availability_reason(obj):
        product = obj.product
        if product.status != Product.Status.ACTIVE or not product.category.is_active:
            return "unavailable"
        if obj.quantity > product.stock_quantity:
            return "insufficient_stock"
        return None


class CartSerializer(serializers.Serializer):
    items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    def _items(self, obj):
        if isinstance(obj, dict):
            return obj.get("items", ())
        return getattr(obj, "prefetched_items", ())

    @extend_schema_field(CartItemSerializer(many=True))
    def get_items(self, obj):
        return CartItemSerializer(
            self._items(obj),
            many=True,
            context=self.context,
        ).data

    @extend_schema_field(serializers.DecimalField(max_digits=40, decimal_places=2))
    def get_subtotal(self, obj):
        subtotal = sum(
            (item.product.price * item.quantity for item in self._items(obj)),
            start=Decimal("0.00"),
        )
        return format(subtotal, ".2f")


class AddCartItemSerializer(serializers.Serializer):
    product_slug = serializers.SlugRelatedField(
        slug_field="slug",
        source="product",
        queryset=Product.objects.all(),
    )
    quantity = serializers.IntegerField(min_value=1)


class ChangeCartItemQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CartValidationErrorSerializer(serializers.Serializer):
    product_slug = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    quantity = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
