import re
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.common.money import STORE_CURRENCY

from .gateways import (
    PaymentGatewayError,
    PaymentVerification,
    TransactionStatus,
    VerificationStatus,
)
from .models import BaleWebhookUpdate, PaymentAttempt
from .services import (
    OrderNotPayable,
    PaymentInventoryInvalid,
    PaymentVerificationInvalid,
    PaymentWindowExpired,
    ProviderTransactionClaimResult,
    accept_payment_attempt_pre_checkout,
    claim_payment_attempt_pre_checkout,
    finalize_verified_payment,
    release_payment_attempt_pre_checkout,
)

BALE_GATEWAY_NAME = "bale"
BALE_PAYLOAD_PATTERN = re.compile(r"\Apay:([0-9a-f]{32})\Z")
PRE_CHECKOUT_REJECTION_MESSAGE = "Payment cannot be completed."
PROCESSING_LEASE = timedelta(minutes=5)


class BaleWebhookInvalid(Exception):
    pass


class BaleWebhookRetry(Exception):
    pass


def record_bale_payment_update(*, update):
    """Durably retain only the structured fields needed for local recovery."""
    pre_checkout = update.get("pre_checkout_query")
    successful_payment = update.get("message", {}).get("successful_payment")
    if pre_checkout is not None:
        event = pre_checkout
        event_type = BaleWebhookUpdate.EventType.PRE_CHECKOUT
        transaction_id = event["id"]
    elif successful_payment is not None:
        event = successful_payment
        event_type = BaleWebhookUpdate.EventType.SUCCESSFUL_PAYMENT
        transaction_id = event["telegram_payment_charge_id"]
    else:
        return None

    attempt = resolve_bale_payment_attempt(event["invoice_payload"])
    record, _ = BaleWebhookUpdate.objects.get_or_create(
        update_id=update["update_id"],
        defaults={
            "event_type": event_type,
            "payment_attempt": attempt,
            "provider_transaction_id": transaction_id,
            "amount": Decimal(event["total_amount"]),
            "currency": event["currency"],
        },
    )
    return record


def process_bale_webhook_update(*, update_id, gateway):
    """Process one durable update; transient failures return it to PENDING."""
    record = _claim_bale_update(update_id=update_id)
    if record is None:
        return BaleWebhookUpdate.objects.get(update_id=update_id)

    try:
        if record.event_type == BaleWebhookUpdate.EventType.PRE_CHECKOUT:
            _process_bale_pre_checkout(record=record, gateway=gateway)
        elif record.event_type == BaleWebhookUpdate.EventType.SUCCESSFUL_PAYMENT:
            _process_bale_successful_payment(record=record, gateway=gateway)
        else:
            raise BaleWebhookInvalid
    except (BaleWebhookRetry, PaymentGatewayError):
        _return_bale_update_to_pending(update_id=record.update_id)
    except (
        BaleWebhookInvalid,
        IntegrityError,
        OrderNotPayable,
        PaymentInventoryInvalid,
        PaymentVerificationInvalid,
        PaymentWindowExpired,
    ):
        _finish_bale_update(
            update_id=record.update_id,
            status=BaleWebhookUpdate.Status.REJECTED,
        )
    else:
        _finish_bale_update(
            update_id=record.update_id,
            status=BaleWebhookUpdate.Status.PROCESSED,
        )
    return BaleWebhookUpdate.objects.get(update_id=record.update_id)


def recoverable_bale_update_ids(*, at=None):
    at = at or timezone.now()
    stale_before = at - PROCESSING_LEASE
    return list(
        BaleWebhookUpdate.objects.filter(
            Q(status=BaleWebhookUpdate.Status.PENDING)
            | Q(
                status=BaleWebhookUpdate.Status.PROCESSING,
                processing_started_at__lte=stale_before,
            )
        )
        .order_by("update_id")
        .values_list("update_id", flat=True)
    )


def _claim_bale_update(*, update_id, at=None):
    at = at or timezone.now()
    stale_before = at - PROCESSING_LEASE
    with transaction.atomic():
        record = BaleWebhookUpdate.objects.select_for_update().get(update_id=update_id)
        if record.status in (
            BaleWebhookUpdate.Status.PROCESSED,
            BaleWebhookUpdate.Status.REJECTED,
        ):
            return None
        if (
            record.status == BaleWebhookUpdate.Status.PROCESSING
            and record.processing_started_at is not None
            and record.processing_started_at > stale_before
        ):
            return None
        record.status = BaleWebhookUpdate.Status.PROCESSING
        record.processing_started_at = at
        record.save(update_fields=("status", "processing_started_at"))
        return record


def _return_bale_update_to_pending(*, update_id):
    BaleWebhookUpdate.objects.filter(
        update_id=update_id,
        status=BaleWebhookUpdate.Status.PROCESSING,
    ).update(
        status=BaleWebhookUpdate.Status.PENDING,
        processing_started_at=None,
    )


def _finish_bale_update(*, update_id, status, at=None):
    at = at or timezone.now()
    BaleWebhookUpdate.objects.filter(
        update_id=update_id,
        status=BaleWebhookUpdate.Status.PROCESSING,
    ).update(
        status=status,
        processing_started_at=None,
        processed_at=at,
    )


def _process_bale_pre_checkout(*, record, gateway):
    attempt = _record_attempt(record, validate_amount=False)
    transaction_id = record.provider_transaction_id
    approved = False
    claimed = False
    if record.currency == STORE_CURRENCY and record.amount == attempt.amount:
        try:
            result = claim_payment_attempt_pre_checkout(
                attempt=attempt,
                provider_transaction_id=transaction_id,
            )
            if result == ProviderTransactionClaimResult.ACCEPTED:
                return
            claimed = True
            approved = True
        except (
            IntegrityError,
            OrderNotPayable,
            PaymentVerificationInvalid,
            PaymentWindowExpired,
        ):
            approved = False

    try:
        # This call cannot be atomic with the following database commit. A timeout
        # releases the local claim; the durable update remains PENDING for recovery.
        gateway.answer_pre_checkout_query(
            pre_checkout_query_id=transaction_id,
            ok=approved,
            error_message=None if approved else PRE_CHECKOUT_REJECTION_MESSAGE,
        )
    except PaymentGatewayError:
        if claimed:
            release_payment_attempt_pre_checkout(
                attempt=attempt,
                provider_transaction_id=transaction_id,
            )
        raise

    if approved and not accept_payment_attempt_pre_checkout(
        attempt=attempt,
        provider_transaction_id=transaction_id,
    ):
        raise BaleWebhookInvalid


def _process_bale_successful_payment(*, record, gateway):
    attempt = _record_attempt(record)
    transaction_id = record.provider_transaction_id

    if attempt.status == PaymentAttempt.Status.SUCCESS:
        if attempt.provider_transaction_id != transaction_id:
            raise BaleWebhookInvalid
        return attempt
    if attempt.status == PaymentAttempt.Status.FAILED:
        if not _recorded_pre_checkout_exists(
            attempt=attempt,
            transaction_id=transaction_id,
        ):
            raise BaleWebhookInvalid
        release_payment_attempt_pre_checkout(
            attempt=attempt,
            provider_transaction_id=transaction_id,
        )
        return attempt
    if attempt.status != PaymentAttempt.Status.PENDING or not attempt.gateway_reference:
        raise BaleWebhookInvalid
    if attempt.provider_transaction_id not in (None, transaction_id):
        raise BaleWebhookInvalid
    if (
        attempt.provider_transaction_id is None
        and attempt.pre_checkout_transaction_id != transaction_id
        # An ambiguous PreCheckout timeout may have succeeded at Bale after its
        # local claim was released. The durable record permits paid inquiry to
        # recover that transaction without treating the webhook itself as proof.
        and not _recorded_pre_checkout_exists(
            attempt=attempt,
            transaction_id=transaction_id,
        )
    ):
        raise BaleWebhookInvalid

    inquiry = gateway.inquire_transaction(transaction_id)
    if inquiry.transaction_id != transaction_id or inquiry.amount != attempt.amount:
        raise BaleWebhookInvalid
    if inquiry.status == TransactionStatus.PENDING:
        raise BaleWebhookRetry

    verification_status = (
        VerificationStatus.SUCCESS
        if inquiry.status == TransactionStatus.PAID
        else VerificationStatus.FAILED
    )
    verification = PaymentVerification(
        status=verification_status,
        gateway_reference=attempt.gateway_reference,
        amount=inquiry.amount,
        currency=attempt.currency,
    )
    result = finalize_verified_payment(
        attempt=attempt,
        verification=verification,
        provider_transaction_id=(
            transaction_id
            if verification_status == VerificationStatus.SUCCESS
            else None
        ),
    )
    if verification_status == VerificationStatus.FAILED:
        release_payment_attempt_pre_checkout(
            attempt=attempt,
            provider_transaction_id=transaction_id,
        )
    return result


def _record_attempt(record, *, validate_amount=True):
    if (
        record.payment_attempt_id is None
        or record.provider_transaction_id is None
        or record.amount is None
    ):
        raise BaleWebhookInvalid
    try:
        attempt = PaymentAttempt.objects.get(
            pk=record.payment_attempt_id,
            gateway=BALE_GATEWAY_NAME,
        )
    except PaymentAttempt.DoesNotExist as exc:
        raise BaleWebhookInvalid from exc
    if attempt.currency != STORE_CURRENCY or (
        validate_amount
        and (record.currency != STORE_CURRENCY or record.amount != attempt.amount)
    ):
        raise BaleWebhookInvalid
    return attempt


def _recorded_pre_checkout_exists(*, attempt, transaction_id):
    return (
        BaleWebhookUpdate.objects.filter(
            payment_attempt=attempt,
            event_type=BaleWebhookUpdate.EventType.PRE_CHECKOUT,
            provider_transaction_id=transaction_id,
        )
        .exclude(status=BaleWebhookUpdate.Status.REJECTED)
        .exists()
    )


def resolve_bale_payment_attempt(payload):
    if not isinstance(payload, str):
        raise BaleWebhookInvalid
    match = BALE_PAYLOAD_PATTERN.fullmatch(payload)
    if match is None:
        raise BaleWebhookInvalid
    try:
        idempotency_key = UUID(hex=match.group(1))
        return PaymentAttempt.objects.get(
            idempotency_key=idempotency_key,
            gateway=BALE_GATEWAY_NAME,
        )
    except (ValueError, PaymentAttempt.DoesNotExist) as exc:
        raise BaleWebhookInvalid from exc
