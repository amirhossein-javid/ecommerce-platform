from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import RejectInputFieldsMixin

from .models import (
    Category,
    Product,
    ProductImage,
    ProductReview,
    ProductReviewReply,
)


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
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=0,
        read_only=True,
    )
    category = CategorySummarySerializer(read_only=True)
    in_stock = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        allow_null=True,
        read_only=True,
    )
    review_count = serializers.IntegerField(min_value=0, read_only=True)

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
            "average_rating",
            "review_count",
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
        max_digits=10,
        decimal_places=0,
        required=False,
    )
    max_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=0,
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


class ProductReviewReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReviewReply
        fields = ("comment", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {
            "comment": {"required": True, "allow_blank": False},
        }

    def validate_comment(self, value):
        comment = value.strip()
        if not comment:
            raise serializers.ValidationError("This field may not be blank.")
        return comment


class PublicProductReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    store_reply = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = (
            "id",
            "rating",
            "comment",
            "author_name",
            "created_at",
            "store_reply",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_author_name(self, obj):
        display_name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
        return display_name or "مشتری نقش‌جهان"

    @extend_schema_field(ProductReviewReplySerializer(allow_null=True))
    def get_store_reply(self, obj):
        try:
            reply = obj.store_reply
        except ProductReviewReply.DoesNotExist:
            return None
        return ProductReviewReplySerializer(reply).data


class OwnProductReviewSerializer(
    RejectInputFieldsMixin,
    serializers.ModelSerializer,
):
    forbidden_fields = frozenset(
        {
            "id",
            "product",
            "product_id",
            "customer",
            "customer_id",
            "author",
            "author_id",
            "status",
            "created_at",
            "updated_at",
        }
    )

    class Meta:
        model = ProductReview
        fields = (
            "id",
            "rating",
            "comment",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")
        extra_kwargs = {
            "rating": {"required": True},
            "comment": {"required": True, "allow_blank": False},
        }

    def validate_comment(self, value):
        comment = value.strip()
        if not comment:
            raise serializers.ValidationError("This field may not be blank.")
        return comment


class ProductReviewAggregateSerializer(serializers.Serializer):
    average_rating = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        allow_null=True,
        read_only=True,
    )
    review_count = serializers.IntegerField(min_value=0, read_only=True)


class ManagedProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "slug")
        read_only_fields = fields


class ManagedProductReviewSerializer(serializers.ModelSerializer):
    product = ManagedProductSummarySerializer(read_only=True)
    customer_display_name = serializers.SerializerMethodField()
    store_reply = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = (
            "id",
            "product",
            "customer_display_name",
            "rating",
            "comment",
            "status",
            "created_at",
            "updated_at",
            "store_reply",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_customer_display_name(self, obj):
        display_name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
        return display_name or f"مشتری شمارهٔ {obj.customer_id}"

    @extend_schema_field(ProductReviewReplySerializer(allow_null=True))
    def get_store_reply(self, obj):
        try:
            reply = obj.store_reply
        except ProductReviewReply.DoesNotExist:
            return None
        return ProductReviewReplySerializer(reply).data


class ProductReviewManagementFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ProductReview.Status,
        required=False,
    )
    has_reply = serializers.BooleanField(required=False)
    search = serializers.CharField(required=False, allow_blank=False, max_length=255)


class ProductReviewModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            ProductReview.Status.APPROVED,
            ProductReview.Status.REJECTED,
        )
    )
