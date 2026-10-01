from django.conf import settings
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomerProfile
from apps.orders.models import Order

from .bale_webhooks import (
    PRE_CHECKOUT_REJECTION_MESSAGE,
    BaleWebhookInvalid,
    process_bale_webhook_update,
    record_bale_payment_update,
)
from .gateways import PaymentGatewayError, get_payment_gateway
from .models import PaymentAttempt
from .serializers import (
    BaleUpdateSerializer,
    BaleWebhookResponseSerializer,
    PaymentAttemptSerializer,
    PaymentErrorSerializer,
    PaymentInitiationRequestSerializer,
    PaymentVerificationRequestSerializer,
)
from .services import (
    OrderNotPayable,
    PaymentInventoryInvalid,
    PaymentVerificationInvalid,
    PaymentWindowExpired,
    initiate_order_payment,
    verify_order_payment,
)

PAYMENT_GATEWAY_UNAVAILABLE_MESSAGE = "Payment gateway is temporarily unavailable."
BALE_WEBHOOK_INVALID_MESSAGE = "Invalid Bale payment update."


@method_decorator(xframe_options_exempt, name="dispatch")
class BaleSmokeTestView(TemplateView):
    template_name = "payments/bale_smoke_test.html"

    def dispatch(self, request, *args, **kwargs):
        if not settings.DEBUG:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class CustomerPaymentMixin:
    permission_classes = (IsAuthenticated,)

    def get_customer_profile(self):
        try:
            return CustomerProfile.objects.get(user=self.request.user)
        except CustomerProfile.DoesNotExist as exc:
            raise NotFound("Customer profile not found.") from exc

    def get_owned_order(self, order_id):
        try:
            return Order.objects.get(
                pk=order_id,
                customer=self.get_customer_profile(),
            )
        except Order.DoesNotExist as exc:
            raise NotFound("Order not found.") from exc


class PaymentInitiationView(CustomerPaymentMixin, APIView):
    @extend_schema(
        request=PaymentInitiationRequestSerializer,
        responses={
            status.HTTP_200_OK: PaymentAttemptSerializer,
            status.HTTP_201_CREATED: PaymentAttemptSerializer,
            status.HTTP_400_BAD_REQUEST: PaymentErrorSerializer,
            status.HTTP_401_UNAUTHORIZED: PaymentErrorSerializer,
            status.HTTP_404_NOT_FOUND: PaymentErrorSerializer,
            status.HTTP_409_CONFLICT: PaymentErrorSerializer,
            status.HTTP_502_BAD_GATEWAY: PaymentErrorSerializer,
            status.HTTP_503_SERVICE_UNAVAILABLE: PaymentErrorSerializer,
        },
        description=(
            "Initiate payment for an owned pending-payment order. The amount and "
            "IRR currency are copied from the authoritative order. Repeated calls "
            "return the existing pending attempt. payment_identifier is the opaque "
            "client handoff value returned by the configured gateway."
        ),
        tags=["Payments"],
    )
    def post(self, request, order_id):
        serializer = PaymentInitiationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.get_owned_order(order_id)
        try:
            attempt, _, created = initiate_order_payment(order=order)
        except (OrderNotPayable, PaymentWindowExpired) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except PaymentGatewayError:
            return Response(
                {"detail": PAYMENT_GATEWAY_UNAVAILABLE_MESSAGE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PaymentVerificationInvalid as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            PaymentAttemptSerializer(attempt).data,
            status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )


class PaymentVerificationView(CustomerPaymentMixin, APIView):
    @extend_schema(
        request=PaymentVerificationRequestSerializer,
        responses={
            status.HTTP_200_OK: PaymentAttemptSerializer,
            status.HTTP_400_BAD_REQUEST: PaymentErrorSerializer,
            status.HTTP_401_UNAUTHORIZED: PaymentErrorSerializer,
            status.HTTP_404_NOT_FOUND: PaymentErrorSerializer,
            status.HTTP_409_CONFLICT: PaymentErrorSerializer,
            status.HTTP_503_SERVICE_UNAVAILABLE: PaymentErrorSerializer,
        },
        description=(
            "Verify untrusted payment return data through the configured gateway, "
            "then atomically finalize a successful payment."
        ),
        tags=["Payments"],
    )
    def post(self, request, order_id, payment_id):
        serializer = PaymentVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.get_owned_order(order_id)
        try:
            attempt = PaymentAttempt.objects.get(pk=payment_id, order=order)
        except PaymentAttempt.DoesNotExist as exc:
            raise NotFound("Payment attempt not found.") from exc

        try:
            attempt = verify_order_payment(
                attempt=attempt,
                callback_data=serializer.validated_data["callback_data"],
            )
        except PaymentVerificationInvalid as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (OrderNotPayable, PaymentInventoryInvalid) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except PaymentGatewayError:
            return Response(
                {"detail": PAYMENT_GATEWAY_UNAVAILABLE_MESSAGE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(PaymentAttemptSerializer(attempt).data)


class BaleWebhookView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=BaleUpdateSerializer,
        responses={
            status.HTTP_200_OK: BaleWebhookResponseSerializer,
            status.HTTP_400_BAD_REQUEST: PaymentErrorSerializer,
        },
        description=(
            "Receive Bale payment updates. This provider endpoint is unauthenticated "
            "because Bale documents no webhook signature; payment success is verified "
            "through inquireTransaction before atomic finalization."
        ),
        auth=[],
        tags=["Payments"],
    )
    def post(self, request):
        try:
            data = request.data
        except ParseError:
            return self._invalid_response()
        serializer = BaleUpdateSerializer(data=data)
        if not serializer.is_valid():
            return self._invalid_response()

        update = serializer.validated_data
        pre_checkout = update.get("pre_checkout_query")
        successful_payment = update.get("message", {}).get("successful_payment")
        if pre_checkout is None and successful_payment is None:
            return Response({"ok": True})

        try:
            record = record_bale_payment_update(update=update)
        except BaleWebhookInvalid:
            gateway = get_payment_gateway()
            if pre_checkout is not None and gateway.name == "bale":
                try:
                    gateway.answer_pre_checkout_query(
                        pre_checkout_query_id=pre_checkout["id"],
                        ok=False,
                        error_message=PRE_CHECKOUT_REJECTION_MESSAGE,
                    )
                except PaymentGatewayError:
                    pass
            return Response({"ok": True})

        gateway = get_payment_gateway()
        if gateway.name == "bale":
            process_bale_webhook_update(
                update_id=record.update_id,
                gateway=gateway,
            )
        return Response({"ok": True})

    @staticmethod
    def _invalid_response():
        return Response(
            {"detail": BALE_WEBHOOK_INVALID_MESSAGE},
            status=status.HTTP_400_BAD_REQUEST,
        )
