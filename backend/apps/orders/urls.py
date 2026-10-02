from django.urls import path

from .views import (
    CheckoutView,
    CustomerOrderCancellationView,
    CustomerOrderDetailView,
    CustomerOrderListView,
)

app_name = "orders"

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/", CustomerOrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>/", CustomerOrderDetailView.as_view(), name="order-detail"),
    path(
        "orders/<int:pk>/cancel/",
        CustomerOrderCancellationView.as_view(),
        name="order-cancel",
    ),
]
