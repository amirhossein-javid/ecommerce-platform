from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListView,
    ProductDetailView,
    ProductListView,
)

app_name = "products"

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<str:slug>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path("products/", ProductListView.as_view(), name="product-list"),
    path(
        "products/<str:slug>/",
        ProductDetailView.as_view(),
        name="product-detail",
    ),
]
