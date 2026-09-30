from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomerProfile

from .models import InventoryReservation, Order, OrderItem
from .serializers import (
    CheckoutErrorSerializer,
    CheckoutOrderSerializer,
    CheckoutRequestSerializer,
    CheckoutValidationErrorSerializer,
)
from .services import (
    CheckoutAddressUnavailable,
    CheckoutCartUnavailable,
    CheckoutInsufficientStock,
    CheckoutProductUnavailable,
    InsufficientAvailableStock,
    ReservationAlreadyExists,
    checkout_customer_cart,
)


def _checkout_order_queryset():
    return Order.objects.prefetch_related(
        Prefetch("items", queryset=OrderItem.objects.order_by("pk")),
        Prefetch(
            "inventory_reservations",
            queryset=InventoryReservation.objects.order_by("pk"),
            to_attr="prefetched_inventory_reservations",
        ),
    )


class CheckoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=CheckoutRequestSerializer,
        responses={
            status.HTTP_201_CREATED: CheckoutOrderSerializer,
            status.HTTP_400_BAD_REQUEST: CheckoutValidationErrorSerializer,
            status.HTTP_401_UNAUTHORIZED: CheckoutErrorSerializer,
            status.HTTP_404_NOT_FOUND: CheckoutErrorSerializer,
        },
        description=(
            "Create a pending-payment order from the authenticated customer's "
            "active cart, using an explicit address or the customer's default. "
            "Prices are recalculated and inventory is reserved for 15 minutes."
        ),
        tags=["Checkout"],
    )
    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            customer = CustomerProfile.objects.get(user=request.user)
        except CustomerProfile.DoesNotExist as exc:
            raise NotFound("Customer profile not found.") from exc

        try:
            order = checkout_customer_cart(
                customer=customer,
                address_id=serializer.validated_data.get("address_id"),
            )
        except CustomerProfile.DoesNotExist as exc:
            raise NotFound("Customer profile not found.") from exc
        except CheckoutAddressUnavailable as exc:
            raise serializers.ValidationError(
                {"detail": ["A usable shipping address is required."]}
            ) from exc
        except CheckoutCartUnavailable as exc:
            raise serializers.ValidationError(
                {"detail": ["An active, non-empty cart is required."]}
            ) from exc
        except CheckoutProductUnavailable as exc:
            raise serializers.ValidationError(
                {"detail": ["The cart contains an unavailable product."]}
            ) from exc
        except (
            CheckoutInsufficientStock,
            InsufficientAvailableStock,
        ) as exc:
            raise serializers.ValidationError(
                {"detail": ["The cart quantity exceeds available stock."]}
            ) from exc
        except ReservationAlreadyExists as exc:
            raise serializers.ValidationError(
                {"detail": ["The cart could not be checked out."]}
            ) from exc

        loaded_order = _checkout_order_queryset().get(pk=order.pk)
        return Response(
            CheckoutOrderSerializer(loaded_order).data,
            status=status.HTTP_201_CREATED,
        )
