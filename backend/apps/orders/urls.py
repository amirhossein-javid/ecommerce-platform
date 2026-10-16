from django.urls import path

from .views import (
    CheckoutView,
    CustomerOrderCancellationView,
    CustomerOrderDetailView,
    CustomerOrderListView,
    ManagementDashboardSummaryView,
    ManagementOrderDetailView,
    ManagementOrderListView,
    ManagementOrderTransitionView,
    ManagementRefundResolutionView,
    ManagementShipmentUpdateView,
)

app_name = "orders"

urlpatterns = [
    path(
        "management/dashboard/summary/",
        ManagementDashboardSummaryView.as_view(),
        name="management-dashboard-summary",
    ),
    path(
        "management/orders/",
        ManagementOrderListView.as_view(),
        name="management-order-list",
    ),
    path(
        "management/orders/<int:pk>/",
        ManagementOrderDetailView.as_view(),
        name="management-order-detail",
    ),
    path(
        "management/orders/<int:pk>/transition/",
        ManagementOrderTransitionView.as_view(),
        name="management-order-transition",
    ),
    path(
        "management/orders/<int:pk>/shipment/",
        ManagementShipmentUpdateView.as_view(),
        name="management-order-shipment",
    ),
    path(
        "management/orders/<int:pk>/resolve-refund/",
        ManagementRefundResolutionView.as_view(),
        name="management-order-resolve-refund",
    ),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/", CustomerOrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>/", CustomerOrderDetailView.as_view(), name="order-detail"),
    path(
        "orders/<int:pk>/cancel/",
        CustomerOrderCancellationView.as_view(),
        name="order-cancel",
    ),
]
