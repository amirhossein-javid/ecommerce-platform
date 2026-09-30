import uuid

from django.db import transaction
from django.db.models import Prefetch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
)
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomerProfile
from apps.products.models import Product, ProductImage

from .models import Cart, CartItem
from .serializers import (
    AddCartItemSerializer,
    CartErrorSerializer,
    CartItemSerializer,
    CartSerializer,
    CartValidationErrorSerializer,
    ChangeCartItemQuantitySerializer,
)
from .services import (
    CartNotActive,
    InsufficientStock,
    ProductUnavailable,
    add_product,
    change_item_quantity,
    get_or_create_active_customer_cart,
    remove_item,
)

CART_TOKEN_HEADER = "X-Cart-Token"

cart_token_request_parameter = OpenApiParameter(
    name=CART_TOKEN_HEADER,
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Guest cart credential. Authenticated requests ignore this header and use "
        "the authenticated customer's cart."
    ),
)

cart_token_response_parameter = OpenApiParameter(
    name=CART_TOKEN_HEADER,
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.HEADER,
    response=True,
    description=(
        "Token associated with a guest cart. Send it as X-Cart-Token on later "
        "guest requests. It is never returned for customer-owned carts."
    ),
)


def _cart_queryset():
    primary_images = ProductImage.objects.filter(is_primary=True).order_by(
        "position", "pk"
    )
    items = (
        CartItem.objects.select_related("product", "product__category")
        .prefetch_related(
            Prefetch(
                "product__images",
                queryset=primary_images,
                to_attr="prefetched_primary_images",
            )
        )
        .order_by("pk")
    )
    return Cart.objects.prefetch_related(
        Prefetch("items", queryset=items, to_attr="prefetched_items")
    )


def _item_queryset():
    return CartItem.objects.select_related(
        "cart",
        "product",
        "product__category",
    ).prefetch_related(
        Prefetch(
            "product__images",
            queryset=ProductImage.objects.filter(is_primary=True).order_by(
                "position", "pk"
            ),
            to_attr="prefetched_primary_images",
        )
    )


class CurrentCartMixin:
    permission_classes = (AllowAny,)

    def resolve_cart(self, *, create=False, with_contents=False):
        if self.request.user.is_authenticated:
            try:
                customer = CustomerProfile.objects.get(user=self.request.user)
            except CustomerProfile.DoesNotExist as exc:
                raise NotFound("Customer profile not found.") from exc

            if create:
                cart, created = get_or_create_active_customer_cart(customer=customer)
                return cart, created
            carts = _cart_queryset() if with_contents else Cart.objects
            return (
                carts.filter(
                    customer=customer,
                    status=Cart.Status.ACTIVE,
                ).first(),
                False,
            )

        token = self.request.headers.get(CART_TOKEN_HEADER)
        if token:
            try:
                parsed_token = uuid.UUID(token)
            except (ValueError, AttributeError) as exc:
                raise NotFound("Cart not found.") from exc
            try:
                carts = _cart_queryset() if with_contents else Cart.objects
                return (
                    carts.get(
                        token=parsed_token,
                        customer__isnull=True,
                        status=Cart.Status.ACTIVE,
                    ),
                    False,
                )
            except Cart.DoesNotExist as exc:
                raise NotFound("Cart not found.") from exc

        if create:
            return Cart.objects.create(), True
        return None, False

    def get_scoped_item(self, pk):
        cart, _ = self.resolve_cart()
        if cart is None:
            raise NotFound("Cart item not found.")
        try:
            return CartItem.objects.get(pk=pk, cart=cart)
        except CartItem.DoesNotExist as exc:
            raise NotFound("Cart item not found.") from exc

    def cart_response(self, cart, *, response_status=status.HTTP_200_OK):
        loaded_cart = (
            cart
            if hasattr(cart, "prefetched_items")
            else _cart_queryset().get(pk=cart.pk)
        )
        response = Response(
            CartSerializer(loaded_cart, context={"request": self.request}).data,
            status=response_status,
        )
        if loaded_cart.customer_id is None:
            response[CART_TOKEN_HEADER] = str(loaded_cart.token)
        return response


class CartView(CurrentCartMixin, APIView):
    @extend_schema(
        parameters=[cart_token_request_parameter, cart_token_response_parameter],
        responses={
            status.HTTP_200_OK: CartSerializer,
            status.HTTP_404_NOT_FOUND: CartErrorSerializer,
        },
        description=(
            "Return the authenticated customer's cart, or a guest cart selected "
            "by X-Cart-Token. A read without a cart returns an empty representation "
            "and does not create persistent state."
        ),
        tags=["Cart"],
    )
    def get(self, request):
        cart, _ = self.resolve_cart(with_contents=True)
        if cart is None:
            return Response(CartSerializer({"items": []}).data)
        return self.cart_response(cart)


class CartItemCreateView(CurrentCartMixin, APIView):
    @extend_schema(
        parameters=[cart_token_request_parameter, cart_token_response_parameter],
        request=AddCartItemSerializer,
        responses={
            status.HTTP_200_OK: CartSerializer,
            status.HTTP_400_BAD_REQUEST: CartValidationErrorSerializer,
            status.HTTP_404_NOT_FOUND: CartErrorSerializer,
        },
        description=(
            "Add a product to the current cart. Creating the first guest item also "
            "creates the guest cart and returns its credential in X-Cart-Token."
        ),
        tags=["Cart"],
    )
    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            cart, _ = self.resolve_cart(create=True)
            try:
                add_product(cart=cart, **serializer.validated_data)
            except ProductUnavailable as exc:
                raise serializers.ValidationError(
                    {"product_slug": ["Product is not currently available."]}
                ) from exc
            except InsufficientStock as exc:
                raise serializers.ValidationError(
                    {"quantity": ["Requested quantity exceeds current stock."]}
                ) from exc
            except Cart.DoesNotExist as exc:
                raise NotFound("Cart not found.") from exc
            except Product.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"product_slug": ["Product is not currently available."]}
                ) from exc

        return self.cart_response(cart)


class CartItemDetailView(CurrentCartMixin, APIView):
    @extend_schema(
        parameters=[cart_token_request_parameter],
        request=ChangeCartItemQuantitySerializer,
        responses={
            status.HTTP_200_OK: CartItemSerializer,
            status.HTTP_400_BAD_REQUEST: CartValidationErrorSerializer,
            status.HTTP_404_NOT_FOUND: CartErrorSerializer,
        },
        description="Change the quantity of an item belonging to the current cart.",
        tags=["Cart"],
    )
    def patch(self, request, pk):
        serializer = ChangeCartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self.get_scoped_item(pk)
        try:
            updated_item = change_item_quantity(
                item=item,
                quantity=serializer.validated_data["quantity"],
            )
        except InsufficientStock as exc:
            raise serializers.ValidationError(
                {"quantity": ["Requested quantity exceeds current stock."]}
            ) from exc
        except (CartNotActive, Cart.DoesNotExist, CartItem.DoesNotExist) as exc:
            raise NotFound("Cart item not found.") from exc

        loaded_item = _item_queryset().get(pk=updated_item.pk)
        return Response(
            CartItemSerializer(
                loaded_item,
                context={"request": request},
            ).data
        )

    @extend_schema(
        parameters=[cart_token_request_parameter],
        responses={
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_404_NOT_FOUND: CartErrorSerializer,
        },
        description="Remove an item belonging to the current cart.",
        tags=["Cart"],
    )
    def delete(self, request, pk):
        item = self.get_scoped_item(pk)
        try:
            remove_item(item=item)
        except (CartNotActive, Cart.DoesNotExist, CartItem.DoesNotExist) as exc:
            raise NotFound("Cart item not found.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
