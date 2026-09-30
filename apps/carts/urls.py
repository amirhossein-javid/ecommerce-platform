from django.urls import path

from .views import CartItemCreateView, CartItemDetailView, CartMergeView, CartView

app_name = "carts"

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart-detail"),
    path("cart/items/", CartItemCreateView.as_view(), name="cart-item-list"),
    path("cart/merge/", CartMergeView.as_view(), name="cart-merge"),
    path(
        "cart/items/<int:pk>/",
        CartItemDetailView.as_view(),
        name="cart-item-detail",
    ),
]
