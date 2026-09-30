from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomerProfile
from apps.orders.models import Order

from .gateways import PaymentGatewayError
from .models import PaymentAttempt
from .serializers import (
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
            "USD currency are copied from the authoritative order. Repeated calls "
            "return the existing pending attempt."
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
