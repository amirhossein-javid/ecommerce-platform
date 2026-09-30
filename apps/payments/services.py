from enum import StrEnum

from django.db import transaction
from django.utils import timezone

from apps.common.money import STORE_CURRENCY
from apps.orders.models import InventoryReservation, Order
from apps.products.models import Product

from .gateways import VerificationStatus, get_payment_gateway
from .models import PaymentAttempt


class PaymentError(Exception):
    """Base exception for rejected payment workflows."""


class OrderNotPayable(PaymentError):
    pass


class PaymentWindowExpired(PaymentError):
    pass


class PaymentVerificationInvalid(PaymentError):
    pass


class PaymentInventoryInvalid(PaymentError):
    pass


class ProviderTransactionClaimResult(StrEnum):
    CLAIMED = "CLAIMED"
    ACCEPTED = "ACCEPTED"


def initiate_order_payment(*, order, at=None, gateway=None):
    """Durably prepare, externally initiate, and persist one payment attempt."""
    gateway = gateway or get_payment_gateway()
    attempt, created = _prepare_payment_attempt(
        order=order,
        gateway_name=gateway.name,
        at=at,
    )
    if attempt.gateway != gateway.name:
        raise PaymentVerificationInvalid("The payment gateway does not match.")
    if attempt.gateway_reference:
        return attempt, attempt.payment_url, created
    if attempt.payment_url:
        raise PaymentVerificationInvalid("Payment initiation state is incomplete.")

    initiation = gateway.initiate(
        order_id=attempt.order_id,
        amount=attempt.amount,
        currency=attempt.currency,
        idempotency_key=attempt.idempotency_key,
    )
    if not initiation.gateway_reference:
        raise PaymentVerificationInvalid(
            "The gateway returned invalid payment initiation data."
        )

    attempt, expired = _persist_payment_initiation(
        attempt=attempt,
        initiation=initiation,
        at=at,
    )
    if expired:
        raise PaymentWindowExpired("The order payment window has expired.")
    return attempt, attempt.payment_url, created


def verify_order_payment(*, attempt, callback_data, at=None, gateway=None):
    """Verify untrusted return data, then atomically finalize its attempt."""
    if attempt.status != PaymentAttempt.Status.PENDING:
        return attempt
    if not attempt.gateway_reference:
        raise PaymentVerificationInvalid("Payment initiation is not complete.")

    gateway = gateway or get_payment_gateway()
    if attempt.gateway != gateway.name:
        raise PaymentVerificationInvalid("The payment gateway does not match.")

    verification = gateway.verify(
        gateway_reference=attempt.gateway_reference,
        callback_data=callback_data,
    )
    if verification.gateway_reference != attempt.gateway_reference:
        raise PaymentVerificationInvalid(
            "The verified payment reference does not match."
        )
    if verification.status not in (
        VerificationStatus.SUCCESS,
        VerificationStatus.FAILED,
    ):
        raise PaymentVerificationInvalid("The gateway returned an invalid status.")
    if verification.status == VerificationStatus.SUCCESS and (
        verification.amount != attempt.amount
        or verification.currency != attempt.currency
    ):
        raise PaymentVerificationInvalid("The verified payment amount does not match.")

    return finalize_verified_payment(
        attempt=attempt,
        verification=verification,
        at=at,
    )


def claim_payment_attempt_pre_checkout(*, attempt, provider_transaction_id, at=None):
    """Reserve one PreCheckout identity without accepting it as provider truth."""
    if not provider_transaction_id:
        raise PaymentVerificationInvalid("The provider transaction is invalid.")

    expired = False
    result = None
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=attempt.order_id)
        locked_attempt = PaymentAttempt.objects.select_for_update().get(
            pk=attempt.pk,
            order=locked_order,
        )
        reservations = _lock_order_reservations(locked_order)
        decision_time = at or timezone.now()
        try:
            _validate_order_is_payable(
                order=locked_order,
                reservations=reservations,
                at=decision_time,
            )
        except PaymentWindowExpired:
            _expire_locked_order(order=locked_order, at=decision_time)
            expired = True

        if not expired:
            if (
                locked_attempt.status != PaymentAttempt.Status.PENDING
                or not locked_attempt.gateway_reference
            ):
                raise OrderNotPayable("The payment attempt is not pending.")
            if locked_attempt.provider_transaction_id == provider_transaction_id:
                result = ProviderTransactionClaimResult.ACCEPTED
            elif locked_attempt.provider_transaction_id is not None:
                raise PaymentVerificationInvalid(
                    "The provider transaction does not match."
                )
            elif locked_attempt.pre_checkout_transaction_id in (
                None,
                provider_transaction_id,
            ):
                if locked_attempt.pre_checkout_transaction_id is None:
                    locked_attempt.pre_checkout_transaction_id = provider_transaction_id
                    locked_attempt.save(
                        update_fields=(
                            "pre_checkout_transaction_id",
                            "updated_at",
                        )
                    )
                if (
                    PaymentAttempt.objects.filter(
                        gateway=locked_attempt.gateway,
                        provider_transaction_id=provider_transaction_id,
                    )
                    .exclude(pk=locked_attempt.pk)
                    .exists()
                ):
                    raise PaymentVerificationInvalid(
                        "The provider transaction is already in use."
                    )
                result = ProviderTransactionClaimResult.CLAIMED
            else:
                raise PaymentVerificationInvalid(
                    "A different provider transaction is being processed."
                )

    if expired:
        raise PaymentWindowExpired("The order payment window has expired.")
    return result


def accept_payment_attempt_pre_checkout(*, attempt, provider_transaction_id, at=None):
    """Commit a provider identity only after Bale accepted PreCheckout."""
    expired = False
    accepted = False
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=attempt.order_id)
        locked_attempt = PaymentAttempt.objects.select_for_update().get(
            pk=attempt.pk,
            order=locked_order,
        )
        reservations = _lock_order_reservations(locked_order)
        decision_time = at or timezone.now()
        try:
            _validate_order_is_payable(
                order=locked_order,
                reservations=reservations,
                at=decision_time,
            )
        except PaymentWindowExpired:
            _expire_locked_order(order=locked_order, at=decision_time)
            expired = True

        if not expired:
            if locked_attempt.provider_transaction_id == provider_transaction_id:
                if (
                    locked_attempt.pre_checkout_transaction_id
                    == provider_transaction_id
                ):
                    locked_attempt.pre_checkout_transaction_id = None
                    locked_attempt.save(
                        update_fields=(
                            "pre_checkout_transaction_id",
                            "updated_at",
                        )
                    )
                accepted = True
            elif (
                locked_attempt.provider_transaction_id is None
                and locked_attempt.pre_checkout_transaction_id
                == provider_transaction_id
            ):
                locked_attempt.provider_transaction_id = provider_transaction_id
                locked_attempt.pre_checkout_transaction_id = None
                locked_attempt.save(
                    update_fields=(
                        "provider_transaction_id",
                        "pre_checkout_transaction_id",
                        "updated_at",
                    )
                )
                accepted = True

    if expired:
        raise PaymentWindowExpired("The order payment window has expired.")
    return accepted


def release_payment_attempt_pre_checkout(*, attempt, provider_transaction_id):
    """Release only the caller's unaccepted PreCheckout claim."""
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=attempt.order_id)
        locked_attempt = PaymentAttempt.objects.select_for_update().get(
            pk=attempt.pk,
            order=locked_order,
        )
        if (
            locked_attempt.provider_transaction_id is None
            and locked_attempt.pre_checkout_transaction_id == provider_transaction_id
        ):
            locked_attempt.pre_checkout_transaction_id = None
            locked_attempt.save(
                update_fields=("pre_checkout_transaction_id", "updated_at")
            )


def finalize_verified_payment(
    *,
    attempt,
    verification,
    provider_transaction_id=None,
    at=None,
):
    """Apply a trusted gateway result using the central atomic finalization path."""
    if verification.gateway_reference != attempt.gateway_reference:
        raise PaymentVerificationInvalid(
            "The verified payment reference does not match."
        )
    if verification.status not in (
        VerificationStatus.SUCCESS,
        VerificationStatus.FAILED,
    ):
        raise PaymentVerificationInvalid("The gateway returned an invalid status.")
    if verification.status == VerificationStatus.SUCCESS and (
        verification.amount != attempt.amount
        or verification.currency != attempt.currency
    ):
        raise PaymentVerificationInvalid("The verified payment amount does not match.")
    if provider_transaction_id == "":
        raise PaymentVerificationInvalid("The provider transaction is invalid.")

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=attempt.order_id)
        locked_attempt = PaymentAttempt.objects.select_for_update().get(
            pk=attempt.pk,
            order=locked_order,
        )
        if locked_attempt.status == PaymentAttempt.Status.SUCCESS:
            if (
                provider_transaction_id is not None
                and locked_attempt.provider_transaction_id != provider_transaction_id
            ):
                raise PaymentVerificationInvalid(
                    "The provider transaction does not match."
                )
            return locked_attempt
        if locked_attempt.status != PaymentAttempt.Status.PENDING:
            return locked_attempt

        if (
            provider_transaction_id is not None
            and locked_attempt.provider_transaction_id
            not in (None, provider_transaction_id)
        ):
            raise PaymentVerificationInvalid("The provider transaction does not match.")

        reservations = _lock_order_reservations(locked_order)
        state_time = at or timezone.now()
        try:
            _validate_order_is_payable(
                order=locked_order,
                reservations=reservations,
                at=state_time,
            )
        except PaymentWindowExpired:
            _expire_locked_order(order=locked_order, at=state_time)
            locked_attempt.refresh_from_db(fields=("status", "updated_at"))
            return locked_attempt

        if verification.status == VerificationStatus.FAILED:
            locked_attempt.status = PaymentAttempt.Status.FAILED
            locked_attempt.save(update_fields=("status", "updated_at"))
            return locked_attempt

        products = list(
            Product.objects.select_for_update()
            .filter(pk__in={item.product_id for item in reservations})
            .order_by("pk")
        )
        products_by_id = {product.pk: product for product in products}
        if len(products_by_id) != len(reservations):
            raise PaymentInventoryInvalid("Reserved inventory is incomplete.")

        try:
            with transaction.atomic():
                finalization_time = at or timezone.now()
                _validate_order_is_payable(
                    order=locked_order,
                    reservations=reservations,
                    at=finalization_time,
                )
                _deduct_locked_stock(
                    products_by_id=products_by_id,
                    reservations=reservations,
                )

                completion_time = at or timezone.now()
                _validate_order_is_payable(
                    order=locked_order,
                    reservations=reservations,
                    at=completion_time,
                )
                InventoryReservation.objects.filter(
                    pk__in=[reservation.pk for reservation in reservations],
                    status=InventoryReservation.Status.ACTIVE,
                ).update(
                    status=InventoryReservation.Status.CONSUMED,
                    updated_at=completion_time,
                )
                locked_order.status = Order.Status.PAID
                locked_order.save(update_fields=("status", "updated_at"))
                locked_attempt.status = PaymentAttempt.Status.SUCCESS
                if provider_transaction_id is not None:
                    locked_attempt.provider_transaction_id = provider_transaction_id
                    locked_attempt.pre_checkout_transaction_id = None
                locked_attempt.save(
                    update_fields=(
                        "status",
                        "provider_transaction_id",
                        "pre_checkout_transaction_id",
                        "updated_at",
                    )
                )
                commit_decision_time = at or timezone.now()
                _validate_payment_deadline(
                    reservations=reservations,
                    at=commit_decision_time,
                )
        except PaymentWindowExpired:
            expiry_time = at or timezone.now()
            _expire_locked_order(order=locked_order, at=expiry_time)
            locked_attempt.refresh_from_db(fields=("status", "updated_at"))
        return locked_attempt


def _prepare_payment_attempt(*, order, gateway_name, at=None):
    if not gateway_name:
        raise PaymentVerificationInvalid("The payment gateway identifier is invalid.")

    expired = False
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        reservations = _lock_order_reservations(locked_order)
        decision_time = at or timezone.now()
        try:
            _validate_order_is_payable(
                order=locked_order,
                reservations=reservations,
                at=decision_time,
            )
        except PaymentWindowExpired:
            _expire_locked_order(order=locked_order, at=decision_time)
            expired = True

        if expired:
            attempt = None
            created = False
        else:
            attempt = (
                PaymentAttempt.objects.select_for_update()
                .filter(order=locked_order, status=PaymentAttempt.Status.PENDING)
                .first()
            )
            created = attempt is None
            if created:
                attempt = PaymentAttempt.objects.create(
                    order=locked_order,
                    amount=locked_order.grand_total,
                    currency=STORE_CURRENCY,
                    gateway=gateway_name,
                )

    if expired:
        raise PaymentWindowExpired("The order payment window has expired.")
    return attempt, created


def _persist_payment_initiation(*, attempt, initiation, at=None):
    expired = False
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=attempt.order_id)
        locked_attempt = PaymentAttempt.objects.select_for_update().get(
            pk=attempt.pk,
            order=locked_order,
        )
        reservations = _lock_order_reservations(locked_order)

        if locked_attempt.gateway_reference:
            if (
                locked_attempt.gateway_reference != initiation.gateway_reference
                or locked_attempt.payment_url != initiation.payment_url
            ):
                raise PaymentVerificationInvalid(
                    "The gateway returned conflicting initiation data."
                )
        else:
            locked_attempt.gateway_reference = initiation.gateway_reference
            locked_attempt.payment_url = initiation.payment_url
            locked_attempt.save(
                update_fields=("gateway_reference", "payment_url", "updated_at")
            )

        decision_time = at or timezone.now()
        if locked_attempt.status != PaymentAttempt.Status.PENDING:
            expired = locked_order.status == Order.Status.EXPIRED
        else:
            try:
                _validate_order_is_payable(
                    order=locked_order,
                    reservations=reservations,
                    at=decision_time,
                )
            except PaymentWindowExpired:
                _expire_locked_order(order=locked_order, at=decision_time)
                expired = True

        locked_attempt.refresh_from_db()
    return locked_attempt, expired


def _deduct_locked_stock(*, products_by_id, reservations):
    for reservation in reservations:
        product = products_by_id[reservation.product_id]
        if product.stock_quantity < reservation.quantity:
            raise PaymentInventoryInvalid("Reserved stock is no longer available.")
        product.stock_quantity -= reservation.quantity
        product.save(update_fields=("stock_quantity", "updated_at"))


def _lock_order_reservations(order):
    return list(
        InventoryReservation.objects.select_for_update()
        .filter(order=order)
        .order_by("pk")
    )


def _validate_order_is_payable(*, order, reservations, at):
    if order.status != Order.Status.PENDING_PAYMENT:
        raise OrderNotPayable("The order is not pending payment.")
    if not reservations:
        raise OrderNotPayable("The order has no inventory reservation.")

    _validate_payment_deadline(reservations=reservations, at=at)
    if any(
        reservation.status != InventoryReservation.Status.ACTIVE
        for reservation in reservations
    ):
        raise OrderNotPayable("The order inventory reservation is not active.")


def _validate_payment_deadline(*, reservations, at):
    if min(reservation.expires_at for reservation in reservations) <= at:
        raise PaymentWindowExpired("The order payment window has expired.")


def _expire_locked_order(*, order, at):
    InventoryReservation.objects.filter(
        order=order,
        status=InventoryReservation.Status.ACTIVE,
    ).update(status=InventoryReservation.Status.RELEASED, updated_at=at)
    PaymentAttempt.objects.filter(
        order=order,
        status=PaymentAttempt.Status.PENDING,
    ).update(status=PaymentAttempt.Status.FAILED, updated_at=at)
    order.status = Order.Status.EXPIRED
    order.save(update_fields=("status", "updated_at"))
