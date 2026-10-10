from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListView,
    OwnProductReviewView,
    ProductDetailView,
    ProductListView,
    ProductReviewAggregateView,
    ProductReviewManagementListView,
    ProductReviewModerationView,
    ProductReviewReplyManagementView,
    PublicProductReviewListView,
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
    path(
        "products/<str:slug>/reviews/",
        PublicProductReviewListView.as_view(),
        name="product-review-list",
    ),
    path(
        "products/<str:slug>/reviews/aggregate/",
        ProductReviewAggregateView.as_view(),
        name="product-review-aggregate",
    ),
    path(
        "products/<str:slug>/reviews/mine/",
        OwnProductReviewView.as_view(),
        name="own-product-review",
    ),
    path(
        "management/reviews/",
        ProductReviewManagementListView.as_view(),
        name="review-management-list",
    ),
    path(
        "management/reviews/<int:pk>/moderate/",
        ProductReviewModerationView.as_view(),
        name="review-management-moderate",
    ),
    path(
        "management/reviews/<int:pk>/reply/",
        ProductReviewReplyManagementView.as_view(),
        name="review-management-reply",
    ),
]
