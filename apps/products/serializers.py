from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Product, ProductImage


class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")
        read_only_fields = fields


class CategorySerializer(CategorySummarySerializer):
    parent = serializers.SerializerMethodField()

    class Meta(CategorySummarySerializer.Meta):
        fields = (*CategorySummarySerializer.Meta.fields, "parent")

    @extend_schema_field(CategorySummarySerializer(allow_null=True))
    def get_parent(self, obj):
        if obj.parent is None or not obj.parent.is_active:
            return None
        return CategorySummarySerializer(obj.parent).data


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "is_primary", "position")
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySummarySerializer(read_only=True)
    in_stock = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "price",
            "in_stock",
            "primary_image",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_in_stock(self, obj):
        return obj.stock_quantity > 0

    @extend_schema_field(ProductImageSerializer(allow_null=True))
    def get_primary_image(self, obj):
        images = getattr(obj, "prefetched_primary_images", ())
        if not images:
            return None
        return ProductImageSerializer(images[0], context=self.context).data


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "description",
            "price",
            "in_stock",
            "images",
        )


class ProductListFilterSerializer(serializers.Serializer):
    category = serializers.SlugField(required=False, allow_unicode=True)
    min_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
    )
    max_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
    )
    in_stock = serializers.BooleanField(required=False)

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise serializers.ValidationError(
                {"max_price": "Must be greater than or equal to min_price."}
            )
        return attrs
