from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Address, CustomerProfile
from .serializers import (
    AddressSerializer,
    CustomerProfileSerializer,
    CustomerRegistrationSerializer,
    LogoutSerializer,
    RegistrationResponseSerializer,
)


class CurrentCustomerProfileMixin:
    def get_customer_profile(self, *, for_update=False):
        profiles = CustomerProfile.objects
        if for_update:
            profiles = profiles.select_for_update()
        try:
            return profiles.get(user=self.request.user)
        except CustomerProfile.DoesNotExist as exc:
            raise NotFound("Customer profile not found.") from exc


class RegistrationView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=CustomerRegistrationSerializer,
        responses={status.HTTP_201_CREATED: RegistrationResponseSerializer},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Registration successful. Please log in."},
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=["Customer Account"]),
    patch=extend_schema(tags=["Customer Account"]),
)
class CustomerProfileView(CurrentCustomerProfileMixin, RetrieveUpdateAPIView):
    serializer_class = CustomerProfileSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return self.get_customer_profile()


@extend_schema_view(
    get=extend_schema(tags=["Customer Account"]),
    post=extend_schema(tags=["Customer Account"]),
)
class AddressListCreateView(CurrentCustomerProfileMixin, ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Address.objects.filter(
            customer_profile=self.get_customer_profile()
        ).order_by("pk")

    def perform_create(self, serializer):
        with transaction.atomic():
            profile = self.get_customer_profile(for_update=True)
            is_first_address = not Address.objects.filter(
                customer_profile=profile
            ).exists()
            serializer.save(
                customer_profile=profile,
                is_default=is_first_address,
            )


@extend_schema_view(
    get=extend_schema(tags=["Customer Account"]),
    patch=extend_schema(tags=["Customer Account"]),
    delete=extend_schema(tags=["Customer Account"]),
)
class AddressDetailView(CurrentCustomerProfileMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get_queryset(self):
        return Address.objects.filter(customer_profile=self.get_customer_profile())

    def perform_destroy(self, instance):
        with transaction.atomic():
            self.get_customer_profile(for_update=True)
            instance.delete()


class SetDefaultAddressView(CurrentCustomerProfileMixin, APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=None,
        responses={status.HTTP_200_OK: AddressSerializer},
        tags=["Customer Account"],
    )
    def post(self, request, pk):
        with transaction.atomic():
            profile = self.get_customer_profile(for_update=True)
            try:
                address = Address.objects.select_for_update().get(
                    pk=pk,
                    customer_profile=profile,
                )
            except Address.DoesNotExist as exc:
                raise NotFound("Address not found.") from exc

            now = timezone.now()
            Address.objects.filter(
                customer_profile=profile,
                is_default=True,
            ).exclude(pk=address.pk).update(
                is_default=False,
                updated_at=now,
            )
            if not address.is_default:
                address.is_default = True
                address.updated_at = now
                address.save(update_fields=("is_default", "updated_at"))

        return Response(AddressSerializer(address).data)


@extend_schema_view(post=extend_schema(tags=["Authentication"]))
class LoginView(TokenObtainPairView):
    pass


@extend_schema_view(post=extend_schema(tags=["Authentication"]))
class RefreshView(TokenRefreshView):
    pass


class LogoutView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=LogoutSerializer,
        responses={status.HTTP_204_NO_CONTENT: None},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
