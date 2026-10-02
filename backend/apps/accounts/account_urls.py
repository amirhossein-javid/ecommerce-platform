from django.urls import path

from .views import (
    AddressDetailView,
    AddressListCreateView,
    CustomerProfileView,
    SetDefaultAddressView,
)

app_name = "account"

urlpatterns = [
    path("profile/", CustomerProfileView.as_view(), name="profile"),
    path("addresses/", AddressListCreateView.as_view(), name="address-list"),
    path(
        "addresses/<int:pk>/",
        AddressDetailView.as_view(),
        name="address-detail",
    ),
    path(
        "addresses/<int:pk>/set-default/",
        SetDefaultAddressView.as_view(),
        name="address-set-default",
    ),
]
