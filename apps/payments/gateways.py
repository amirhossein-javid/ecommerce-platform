from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from django.conf import settings
from django.utils.module_loading import import_string


class PaymentGatewayError(Exception):
    """Base exception for gateway communication or configuration failures."""


class PaymentGatewayUnavailable(PaymentGatewayError):
    pass


class VerificationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PaymentInitiation:
    gateway_reference: str
    payment_url: str


@dataclass(frozen=True)
class PaymentVerification:
    status: VerificationStatus
    gateway_reference: str
    amount: Decimal | None = None
    currency: str | None = None


class PaymentGateway(Protocol):
    name: str

    def initiate(
        self,
        *,
        order_id: int,
        amount: Decimal,
        currency: str,
        idempotency_key: UUID,
    ) -> PaymentInitiation: ...

    def verify(
        self,
        *,
        gateway_reference: str,
        callback_data: dict[str, Any],
    ) -> PaymentVerification: ...


class UnavailablePaymentGateway:
    """Safe default until a real provider adapter is configured."""

    name = "unconfigured"

    def initiate(self, **kwargs):
        raise PaymentGatewayUnavailable("No payment gateway is configured.")

    def verify(self, **kwargs):
        raise PaymentGatewayUnavailable("No payment gateway is configured.")


def get_payment_gateway() -> PaymentGateway:
    gateway_path = getattr(
        settings,
        "PAYMENT_GATEWAY_CLASS",
        "apps.payments.gateways.UnavailablePaymentGateway",
    )
    return import_string(gateway_path)()
