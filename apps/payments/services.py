from django.db import transaction
from django.utils import timezone

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
    if attempt.gateway_reference and attempt.payment_url:
        return attempt, attempt.payment_url, created
    if attempt.gateway_reference or attempt.payment_url:
        raise PaymentVerificationInvalid("Payment initiation state is incomplete.")

    initiation = gateway.initiate(
        order_id=attempt.order_id,
        amount=attempt.amount,
        currency=attempt.currency,
        idempotency_key=attempt.idempotency_key,
    )
    if not initiation.gateway_reference or not initiation.payment_url:
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

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=attempt.order_id)
        locked_attempt = PaymentAttempt.objects.select_for_update().get(
            pk=attempt.pk,
            order=locked_order,
        )
        if locked_attempt.status != PaymentAttempt.Status.PENDING:
            return locked_attempt

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
                locked_attempt.save(update_fields=("status", "updated_at"))
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
                    currency="USD",
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
