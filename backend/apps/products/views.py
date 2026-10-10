from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomerProfile

from .models import Category, Product, ProductImage, ProductReview
from .serializers import (
    CategorySerializer,
    OwnProductReviewSerializer,
    ProductDetailSerializer,
    ProductListFilterSerializer,
    ProductListSerializer,
    ProductReviewAggregateSerializer,
    PublicProductReviewSerializer,
)


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DeterministicOrderingFilter(filters.OrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if ordering and not any(field.lstrip("-") == "pk" for field in ordering):
            return (*ordering, "pk")
        return ordering


@extend_schema_view(get=extend_schema(tags=["Catalog"]))
class CategoryListView(ListAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = (
        Category.objects.filter(is_active=True)
        .select_related("parent")
        .order_by("name", "pk")
    )


@extend_schema_view(get=extend_schema(tags=["Catalog"]))
class CategoryDetailView(RetrieveAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = CategorySerializer
    lookup_field = "slug"
    queryset = Category.objects.filter(is_active=True).select_related("parent")


@extend_schema_view(
    get=extend_schema(
        parameters=[ProductListFilterSerializer],
        tags=["Catalog"],
    )
)
class ProductListView(ListAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = ProductListSerializer
    pagination_class = ProductPagination
    filter_backends = (filters.SearchFilter, DeterministicOrderingFilter)
    search_fields = ("name", "description")
    ordering_fields = ("price", "created_at")
    ordering = ("-created_at", "pk")

    def get_queryset(self):
        queryset = (
            Product.objects.filter(
                status=Product.Status.ACTIVE,
                category__is_active=True,
            )
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.filter(is_primary=True).order_by(
                        "position", "pk"
                    ),
                    to_attr="prefetched_primary_images",
                )
            )
        )
        filter_serializer = ProductListFilterSerializer(
            data=self.request.query_params.dict()
        )
        filter_serializer.is_valid(raise_exception=True)
        filters_data = filter_serializer.validated_data

        if category_slug := filters_data.get("category"):
            queryset = queryset.filter(category__slug=category_slug)
        if (min_price := filters_data.get("min_price")) is not None:
            queryset = queryset.filter(price__gte=min_price)
        if (max_price := filters_data.get("max_price")) is not None:
            queryset = queryset.filter(price__lte=max_price)
        if (in_stock := filters_data.get("in_stock")) is not None:
            stock_filter = (
                {"stock_quantity__gt": 0} if in_stock else {"stock_quantity": 0}
            )
            queryset = queryset.filter(**stock_filter)

        return queryset


@extend_schema_view(get=extend_schema(tags=["Catalog"]))
class ProductDetailView(RetrieveAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"
    queryset = (
        Product.objects.filter(
            status=Product.Status.ACTIVE,
            category__is_active=True,
        )
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ProductImage.objects.order_by("position", "pk"),
            )
        )
    )


class ProductReviewPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


def get_public_product(slug):
    try:
        return Product.objects.get(
            slug=slug,
            status=Product.Status.ACTIVE,
            category__is_active=True,
        )
    except Product.DoesNotExist as exc:
        raise NotFound("Product not found.") from exc


class DuplicateProductReview(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A review already exists for this product."
    default_code = "duplicate_review"


@extend_schema_view(get=extend_schema(tags=["Product Reviews"]))
class PublicProductReviewListView(ListAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = PublicProductReviewSerializer
    pagination_class = ProductReviewPagination

    def get_queryset(self):
        product = get_public_product(self.kwargs["slug"])
        return ProductReview.objects.filter(
            product=product,
            status=ProductReview.Status.APPROVED,
        ).select_related("customer")


class ProductReviewAggregateView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        responses={status.HTTP_200_OK: ProductReviewAggregateSerializer},
        tags=["Product Reviews"],
    )
    def get(self, request, slug):
        product = get_public_product(slug)
        aggregate = ProductReview.objects.filter(
            product=product,
            status=ProductReview.Status.APPROVED,
        ).aggregate(
            average_rating=Avg("rating"),
            review_count=Count("id"),
        )
        average = aggregate["average_rating"]
        if average is not None:
            average = Decimal(average).quantize(
                Decimal("0.1"),
                rounding=ROUND_HALF_UP,
            )
        serializer = ProductReviewAggregateSerializer(
            {"average_rating": average, "review_count": aggregate["review_count"]}
        )
        return Response(serializer.data)


class OwnProductReviewView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_throttles(self):
        self.throttle_scope = (
            "review_mutation" if self.request.method in {"POST", "DELETE"} else None
        )
        return super().get_throttles()

    def get_customer_profile(self):
        try:
            return CustomerProfile.objects.get(user=self.request.user)
        except CustomerProfile.DoesNotExist as exc:
            raise NotFound("Customer profile not found.") from exc

    def get_review(self, *, product, customer):
        try:
            return ProductReview.objects.get(product=product, customer=customer)
        except ProductReview.DoesNotExist as exc:
            raise NotFound("Review not found.") from exc

    @extend_schema(
        responses={status.HTTP_200_OK: OwnProductReviewSerializer},
        tags=["Product Reviews"],
    )
    def get(self, request, slug):
        product = get_public_product(slug)
        customer = self.get_customer_profile()
        review = self.get_review(product=product, customer=customer)
        return Response(OwnProductReviewSerializer(review).data)

    @extend_schema(
        request=OwnProductReviewSerializer,
        responses={status.HTTP_201_CREATED: OwnProductReviewSerializer},
        tags=["Product Reviews"],
    )
    def post(self, request, slug):
        product = get_public_product(slug)
        customer = self.get_customer_profile()
        serializer = OwnProductReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                review = serializer.save(product=product, customer=customer)
        except IntegrityError as exc:
            raise DuplicateProductReview from exc
        return Response(
            OwnProductReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=None,
        responses={status.HTTP_204_NO_CONTENT: None},
        tags=["Product Reviews"],
    )
    def delete(self, request, slug):
        product = get_public_product(slug)
        customer = self.get_customer_profile()
        review = self.get_review(product=product, customer=customer)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
