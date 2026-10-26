from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomerProfile
from apps.payments.models import PaymentAttempt
from apps.products.models import Product

from .lifecycle import (
    OrderLifecycleError,
    cancel_order,
    resolve_order_refund,
    transition_order,
)
from .models import InventoryReservation, Order, OrderItem, OrderStatusHistory, Shipment
from .serializers import (
    CheckoutErrorSerializer,
    CheckoutOrderSerializer,
    CheckoutRequestSerializer,
    CheckoutValidationErrorSerializer,
    CustomerOrderDetailSerializer,
    CustomerOrderListSerializer,
    ManagementDashboardSummarySerializer,
    ManagementOrderDetailSerializer,
    ManagementOrderFilterSerializer,
    ManagementOrderListSerializer,
    ManagementOrderTransitionSerializer,
    ManagementShipmentSerializer,
    OrderCancellationSerializer,
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

LOW_STOCK_THRESHOLD = 5


def _checkout_order_queryset():
    return Order.objects.prefetch_related(
        Prefetch("items", queryset=OrderItem.objects.order_by("pk")),
        Prefetch(
            "inventory_reservations",
            queryset=InventoryReservation.objects.order_by("pk"),
            to_attr="prefetched_inventory_reservations",
        ),
    )


class CustomerOrderPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CustomerOrderMixin:
    permission_classes = (IsAuthenticated,)

    def get_customer_profile(self):
        try:
            return CustomerProfile.objects.get(user=self.request.user)
        except CustomerProfile.DoesNotExist as exc:
            raise NotFound("Customer profile not found.") from exc

    def get_queryset(self):
        return Order.objects.filter(customer=self.get_customer_profile())


@extend_schema_view(
    get=extend_schema(
        responses={
            status.HTTP_200_OK: CustomerOrderListSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: CheckoutErrorSerializer,
            status.HTTP_404_NOT_FOUND: CheckoutErrorSerializer,
        },
        tags=["Orders"],
    )
)
class CustomerOrderListView(CustomerOrderMixin, ListAPIView):
    serializer_class = CustomerOrderListSerializer
    pagination_class = CustomerOrderPagination

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch("items", queryset=OrderItem.objects.order_by("pk"))
            )
            .order_by("-created_at", "-pk")
        )


@extend_schema_view(
    get=extend_schema(
        responses={
            status.HTTP_200_OK: CustomerOrderDetailSerializer,
            status.HTTP_401_UNAUTHORIZED: CheckoutErrorSerializer,
            status.HTTP_404_NOT_FOUND: CheckoutErrorSerializer,
        },
        tags=["Orders"],
    )
)
class CustomerOrderDetailView(CustomerOrderMixin, RetrieveAPIView):
    serializer_class = CustomerOrderDetailSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch("items", queryset=OrderItem.objects.order_by("pk"))
            )
        )


class CustomerOrderCancellationView(CustomerOrderMixin, GenericAPIView):
    serializer_class = OrderCancellationSerializer

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: OrderCancellationSerializer,
            status.HTTP_401_UNAUTHORIZED: CheckoutErrorSerializer,
            status.HTTP_404_NOT_FOUND: CheckoutErrorSerializer,
            status.HTTP_409_CONFLICT: CheckoutErrorSerializer,
        },
        description=(
            "Cancel an owned pending-payment, paid, or processing order. "
            "The operation is idempotent for the same customer command."
        ),
        tags=["Orders"],
    )
    def post(self, request, pk):
        order = self.get_object()
        try:
            result = cancel_order(
                order=order,
                actor_type=OrderStatusHistory.ActorType.CUSTOMER,
                actor_user=request.user,
            )
        except OrderLifecycleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(OrderCancellationSerializer(result.order).data)


class CheckoutView(APIView):
    permission_classes = (IsAuthenticated,)
    throttle_scope = "checkout"

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


class OrderManagementPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or not user.is_active or not user.is_staff:
            return False
        return view.has_operator_permission(user, request.method)


class OrderManagementMixin:
    permission_classes = (OrderManagementPermission,)

    @staticmethod
    def can_view_orders(user):
        return user.has_perm("orders.view_order") or user.has_perm(
            "orders.change_order"
        )

    def get_management_order(self, pk, *, for_update=False):
        queryset = Order.objects
        if for_update:
            queryset = queryset.select_for_update()
        try:
            return queryset.get(pk=pk)
        except Order.DoesNotExist as exc:
            raise NotFound("Order not found.") from exc


def _management_order_queryset():
    return (
        Order.objects.select_related("customer", "customer__user", "shipment")
        .annotate(item_count=Coalesce(Sum("items__quantity"), 0))
        .order_by("-created_at", "-pk")
    )


class ManagementDashboardSummaryView(OrderManagementMixin, APIView):
    def has_operator_permission(self, user, method):
        return method in {"GET", "HEAD", "OPTIONS"} and self.can_view_orders(user)

    @extend_schema(
        responses={status.HTTP_200_OK: ManagementDashboardSummarySerializer},
        tags=["Order Management"],
    )
    def get(self, request):
        successful_attempt = PaymentAttempt.objects.filter(
            order_id=OuterRef("pk"), status=PaymentAttempt.Status.SUCCESS
        )
        successful_revenue = (
            Order.objects.annotate(has_successful_payment=Exists(successful_attempt))
            .filter(has_successful_payment=True)
            .aggregate(total=Sum("grand_total"))["total"]
            or 0
        )
        data = {
            "order_count": Order.objects.count(),
            "successful_revenue": successful_revenue,
            "pending_fulfillment_count": Order.objects.filter(
                status__in=(
                    Order.Status.PAID,
                    Order.Status.PROCESSING,
                    Order.Status.SHIPPED,
                )
            ).count(),
            "low_stock_product_count": Product.objects.filter(
                status=Product.Status.ACTIVE,
                category__is_active=True,
                stock_quantity__lte=LOW_STOCK_THRESHOLD,
            ).count(),
            "low_stock_threshold": LOW_STOCK_THRESHOLD,
        }
        return Response(ManagementDashboardSummarySerializer(data).data)


class ManagementOrderListView(OrderManagementMixin, ListAPIView):
    serializer_class = ManagementOrderListSerializer
    pagination_class = CustomerOrderPagination

    def has_operator_permission(self, user, method):
        return method in {"GET", "HEAD", "OPTIONS"} and self.can_view_orders(user)

    def get_queryset(self):
        filters = ManagementOrderFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = _management_order_queryset()
        if order_status := filters.validated_data.get("status"):
            queryset = queryset.filter(status=order_status)
        if search := filters.validated_data.get("search"):
            query = (
                Q(customer__user__email__icontains=search)
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(shipping_recipient_first_name__icontains=search)
                | Q(shipping_recipient_last_name__icontains=search)
            )
            if search.isdecimal():
                query |= Q(pk=int(search))
            queryset = queryset.filter(query)
        return queryset


class ManagementOrderDetailView(OrderManagementMixin, RetrieveAPIView):
    serializer_class = ManagementOrderDetailSerializer

    def has_operator_permission(self, user, method):
        return method in {"GET", "HEAD", "OPTIONS"} and self.can_view_orders(user)

    def get_queryset(self):
        return _management_order_queryset().prefetch_related(
            Prefetch("items", queryset=OrderItem.objects.order_by("pk")),
            Prefetch(
                "status_history",
                queryset=OrderStatusHistory.objects.select_related(
                    "actor_user"
                ).order_by("created_at", "pk"),
            ),
        )


class ManagementOrderTransitionView(OrderManagementMixin, APIView):
    def has_operator_permission(self, user, method):
        return method == "POST" and user.has_perm("orders.change_order")

    @extend_schema(
        request=ManagementOrderTransitionSerializer,
        responses={status.HTTP_200_OK: ManagementOrderDetailSerializer},
        description=(
            "Apply an operator transition. A retry succeeds only while the order "
            "remains at the requested status and its latest history records the "
            "same transition by the same operator. Different actors and stale "
            "retries after a subsequent transition receive 409."
        ),
        tags=["Order Management"],
    )
    def post(self, request, pk):
        serializer = ManagementOrderTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.get_management_order(pk)
        target_status = serializer.validated_data["status"]
        try:
            if target_status == Order.Status.CANCELLED:
                result = cancel_order(
                    order=order,
                    actor_type=OrderStatusHistory.ActorType.OPERATOR,
                    actor_user=request.user,
                )
            else:
                result = transition_order(
                    order=order,
                    to_status=target_status,
                    actor_type=OrderStatusHistory.ActorType.OPERATOR,
                    actor_user=request.user,
                )
        except OrderLifecycleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        loaded = ManagementOrderDetailView().get_queryset().get(pk=result.order.pk)
        return Response(ManagementOrderDetailSerializer(loaded).data)


class ManagementShipmentUpdateView(OrderManagementMixin, APIView):
    def has_operator_permission(self, user, method):
        return (
            method == "PATCH"
            and self.can_view_orders(user)
            and user.has_perm("orders.change_shipment")
        )

    @extend_schema(
        request=ManagementShipmentSerializer,
        responses={status.HTTP_200_OK: ManagementOrderDetailSerializer},
        tags=["Order Management"],
    )
    def patch(self, request, pk):
        serializer = ManagementShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                order = self.get_management_order(pk, for_update=True)
                try:
                    shipment = Shipment.objects.select_for_update().get(order=order)
                except Shipment.DoesNotExist as exc:
                    raise NotFound("Shipment not found.") from exc
                shipment.carrier = serializer.validated_data["carrier"]
                shipment.tracking_number = serializer.validated_data["tracking_number"]
                shipment.save(
                    update_fields=("carrier", "tracking_number", "updated_at")
                )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_409_CONFLICT)
        loaded = ManagementOrderDetailView().get_queryset().get(pk=pk)
        return Response(ManagementOrderDetailSerializer(loaded).data)


class ManagementRefundResolutionView(OrderManagementMixin, APIView):
    def has_operator_permission(self, user, method):
        return method == "POST" and user.has_perm("orders.change_order")

    @extend_schema(
        request=None,
        responses={status.HTTP_200_OK: ManagementOrderDetailSerializer},
        tags=["Order Management"],
    )
    def post(self, request, pk):
        order = self.get_management_order(pk)
        try:
            result = resolve_order_refund(order=order, operator=request.user)
        except OrderLifecycleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        loaded = ManagementOrderDetailView().get_queryset().get(pk=result.order.pk)
        return Response(ManagementOrderDetailSerializer(loaded).data)
