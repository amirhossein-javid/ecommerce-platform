from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListFilterSerializer,
    ProductListSerializer,
)


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


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
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
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
