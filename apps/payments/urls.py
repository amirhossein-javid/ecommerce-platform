from django.urls import path

from .views import BaleWebhookView, PaymentInitiationView, PaymentVerificationView

app_name = "payments"

urlpatterns = [
    path(
        "payments/bale/webhook/",
        BaleWebhookView.as_view(),
        name="bale-webhook",
    ),
    path(
        "orders/<int:order_id>/payments/",
        PaymentInitiationView.as_view(),
        name="payment-initiate",
    ),
    path(
        "orders/<int:order_id>/payments/<int:payment_id>/verify/",
        PaymentVerificationView.as_view(),
        name="payment-verify",
    ),
]
