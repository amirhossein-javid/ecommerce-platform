from decimal import Decimal
from typing import Any
from uuid import UUID

import requests
from django.conf import settings

from apps.common.money import STORE_CURRENCY

from .gateways import (
    PaymentGatewayError,
    PaymentGatewayUnavailable,
    PaymentInitiation,
    PaymentTransaction,
    TransactionStatus,
)

BALE_API_BASE_URL = "https://tapi.bale.ai"
BALE_INVOICE_TITLE = "Order payment"
BALE_INVOICE_DESCRIPTION_TEMPLATE = "Payment for order {order_id}"
BALE_PRICE_LABEL = "Order total"
BALE_PAYLOAD_PREFIX = "pay:"
BALE_MAX_REFERENCE_LENGTH = 255


class BaleGateway:
    name = "bale"

    def __init__(
        self,
        *,
        bot_token=None,
        provider_token=None,
        connect_timeout=None,
        read_timeout=None,
        session=None,
    ):
        self._bot_token = settings.BALE_BOT_TOKEN if bot_token is None else bot_token
        self._provider_token = (
            settings.BALE_PROVIDER_TOKEN if provider_token is None else provider_token
        )
        self._connect_timeout = (
            settings.BALE_CONNECT_TIMEOUT
            if connect_timeout is None
            else connect_timeout
        )
        self._read_timeout = (
            settings.BALE_READ_TIMEOUT if read_timeout is None else read_timeout
        )
        self._session = session or requests.Session()

    def __repr__(self):
        return "<BaleGateway name='bale'>"

    def initiate(
        self,
        *,
        order_id: int,
        amount: Decimal,
        currency: str,
        idempotency_key: UUID,
    ) -> PaymentInitiation:
        self._validate_configuration(require_provider_token=True)
        integer_amount = self._validate_irr_amount(amount=amount, currency=currency)
        payload = f"{BALE_PAYLOAD_PREFIX}{idempotency_key.hex}"
        if not 1 <= len(payload.encode("utf-8")) <= 128:
            raise PaymentGatewayError("The Bale invoice payload is invalid.")

        result = self._request(
            "createInvoiceLink",
            {
                "title": BALE_INVOICE_TITLE,
                "description": BALE_INVOICE_DESCRIPTION_TEMPLATE.format(
                    order_id=order_id
                ),
                "payload": payload,
                "provider_token": self._provider_token,
                "prices": [
                    {
                        "label": BALE_PRICE_LABEL,
                        "amount": integer_amount,
                    }
                ],
            },
        )
        if (
            not isinstance(result, str)
            or not result
            or len(result) > BALE_MAX_REFERENCE_LENGTH
        ):
            raise PaymentGatewayError("Bale returned an invalid payment identifier.")
        return PaymentInitiation(gateway_reference=result)

    def inquire_transaction(self, transaction_id: str) -> PaymentTransaction:
        self._validate_configuration(require_provider_token=False)
        if not isinstance(transaction_id, str) or not transaction_id:
            raise PaymentGatewayError("The Bale transaction identifier is invalid.")

        result = self._request(
            "inquireTransaction",
            {"transaction_id": transaction_id},
        )
        if not isinstance(result, dict):
            raise PaymentGatewayError("Bale returned an invalid transaction.")

        returned_id = result.get("id")
        status_value = result.get("status")
        amount = result.get("amount")
        user_id = result.get("userID")
        created_at = result.get("createdAt")
        if (
            not isinstance(returned_id, str)
            or not returned_id
            or returned_id != transaction_id
            or not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount < 0
            or not isinstance(user_id, int)
            or isinstance(user_id, bool)
            or not isinstance(created_at, int)
            or isinstance(created_at, bool)
        ):
            raise PaymentGatewayError("Bale returned an invalid transaction.")
        try:
            transaction_status = TransactionStatus(status_value)
        except (TypeError, ValueError):
            raise PaymentGatewayError(
                "Bale returned an invalid transaction status."
            ) from None

        return PaymentTransaction(
            transaction_id=returned_id,
            status=transaction_status,
            amount=Decimal(amount),
            user_id=user_id,
            created_at=created_at,
        )

    def answer_pre_checkout_query(
        self,
        *,
        pre_checkout_query_id: str,
        ok: bool,
        error_message: str | None = None,
    ) -> None:
        self._validate_configuration(require_provider_token=False)
        if not pre_checkout_query_id:
            raise PaymentGatewayError("The Bale pre-checkout identifier is invalid.")
        payload = {
            "pre_checkout_query_id": pre_checkout_query_id,
            "ok": ok,
        }
        if not ok:
            if not error_message:
                raise PaymentGatewayError("A Bale rejection message is required.")
            payload["error_message"] = error_message
        if self._request("answerPreCheckoutQuery", payload) is not True:
            raise PaymentGatewayError("Bale did not accept the pre-checkout answer.")

    def set_webhook(self, url: str) -> None:
        self._validate_configuration(require_provider_token=False)
        if self._request("setWebhook", {"url": url}) is not True:
            raise PaymentGatewayError("Bale did not accept the webhook URL.")

    def verify(self, **kwargs):
        raise PaymentGatewayUnavailable(
            "Bale payment-event verification is not configured."
        )

    def _request(self, method: str, payload: dict[str, Any]):
        url = f"{BALE_API_BASE_URL}/bot{self._bot_token}/{method}"
        try:
            response = self._session.post(
                url,
                json=payload,
                timeout=(self._connect_timeout, self._read_timeout),
            )
            response.raise_for_status()
        except requests.RequestException:
            raise PaymentGatewayUnavailable("Bale gateway request failed.") from None

        try:
            body = response.json()
        except ValueError:
            raise PaymentGatewayError("Bale returned an invalid response.") from None
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise PaymentGatewayError("Bale rejected the gateway request.")
        if "result" not in body:
            raise PaymentGatewayError("Bale returned an invalid response.")
        return body["result"]

    def _validate_configuration(self, *, require_provider_token: bool):
        if not self._bot_token or (require_provider_token and not self._provider_token):
            raise PaymentGatewayUnavailable("Bale gateway is not configured.")

    @staticmethod
    def _validate_irr_amount(*, amount: Decimal, currency: str) -> int:
        if currency != STORE_CURRENCY or amount != amount.to_integral_value():
            raise PaymentGatewayError("The Bale payment amount is invalid.")
        integer_amount = int(amount)
        if integer_amount < 0:
            raise PaymentGatewayError("The Bale payment amount is invalid.")
        return integer_amount
