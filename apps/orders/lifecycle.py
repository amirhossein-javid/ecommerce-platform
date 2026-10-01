from dataclasses import dataclass

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.products.models import Product

from .models import (
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatusHistory,
    Shipment,
)


class OrderLifecycleError(Exception):
    """Base exception for rejected order lifecycle operations."""


class InvalidOrderTransition(OrderLifecycleError):
    pass


class InvalidOrderTransitionActor(OrderLifecycleError):
    pass


class RefundResolutionError(OrderLifecycleError):
    pass


class OrderCancellationInventoryInvalid(OrderLifecycleError):
    pass


class ShipmentDetailsRequired(OrderLifecycleError):
    pass


@dataclass(frozen=True)
class OrderTransitionResult:
    order: Order
    changed: bool


ALLOWED_TRANSITIONS = {
    Order.Status.PENDING_PAYMENT: frozenset(
        {Order.Status.PAID, Order.Status.CANCELLED, Order.Status.EXPIRED}
    ),
    Order.Status.PAID: frozenset({Order.Status.PROCESSING, Order.Status.CANCELLED}),
    Order.Status.PROCESSING: frozenset({Order.Status.SHIPPED, Order.Status.CANCELLED}),
    Order.Status.SHIPPED: frozenset({Order.Status.DELIVERED}),
    Order.Status.DELIVERED: frozenset(),
    Order.Status.CANCELLED: frozenset(),
    Order.Status.EXPIRED: frozenset(),
}

_COMPOUND_SYSTEM_TARGETS = frozenset({Order.Status.PAID, Order.Status.EXPIRED})
_PUBLIC_ACTORS_BY_TARGET = {
    Order.Status.PROCESSING: frozenset({OrderStatusHistory.ActorType.OPERATOR}),
    Order.Status.SHIPPED: frozenset({OrderStatusHistory.ActorType.OPERATOR}),
    Order.Status.DELIVERED: frozenset({OrderStatusHistory.ActorType.OPERATOR}),
    Order.Status.CANCELLED: frozenset(
        {
            OrderStatusHistory.ActorType.CUSTOMER,
            OrderStatusHistory.ActorType.OPERATOR,
        }
    ),
}
_STATUS_TIMESTAMP_FIELDS = {
    Order.Status.PAID: "paid_at",
    Order.Status.PROCESSING: "processing_at",
    Order.Status.SHIPPED: "shipped_at",
    Order.Status.DELIVERED: "delivered_at",
    Order.Status.CANCELLED: "cancelled_at",
}


def transition_order(
    *,
    order,
    from_status,
    to_status,
    actor_type,
    actor_user,
    at=None,
):
    """Run one customer/operator lifecycle command against fresh locked state."""
    source_status = _normalize_status(from_status)
    target_status = _normalize_status(to_status)
    if target_status == Order.Status.CANCELLED:
        if target_status not in ALLOWED_TRANSITIONS[source_status]:
            raise InvalidOrderTransition(
                f"Order cannot transition from {source_status} to {target_status}."
            )
        return cancel_order(
            order=order,
            actor_type=actor_type,
            actor_user=actor_user,
            expected_status=source_status,
            at=at,
        )
    if target_status in _COMPOUND_SYSTEM_TARGETS:
        raise InvalidOrderTransition(
            f"The {target_status} transition requires its aggregate workflow."
        )
    if target_status not in ALLOWED_TRANSITIONS[source_status]:
        raise InvalidOrderTransition(
            f"Order cannot transition from {source_status} to {target_status}."
        )

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        normalized_actor_type = _validate_public_actor(
            order=locked_order,
            to_status=target_status,
            actor_type=actor_type,
            actor_user=actor_user,
        )
        if locked_order.status == target_status:
            if _matching_transition_exists(
                order=locked_order,
                from_status=source_status,
                to_status=target_status,
                actor_type=normalized_actor_type,
                actor_user=actor_user,
            ):
                return OrderTransitionResult(order=locked_order, changed=False)
            raise InvalidOrderTransition(
                "The order reached this status through a different command."
            )
        if locked_order.status != source_status:
            raise InvalidOrderTransition(
                f"Expected order status {source_status}, found {locked_order.status}."
            )
        _prepare_locked_fulfillment_transition(
            order=locked_order,
            to_status=target_status,
        )
        return _apply_locked_transition(
            order=locked_order,
            from_status=source_status,
            to_status=target_status,
            actor_type=normalized_actor_type,
            actor_user=actor_user,
            at=at,
        )


def cancel_order(
    *,
    order,
    actor_type,
    actor_user,
    expected_status=None,
    at=None,
):
    """Cancel an eligible order and apply all inventory/payment side effects."""
    normalized_expected_status = (
        _normalize_status(expected_status) if expected_status is not None else None
    )
    cancellable_statuses = (
        Order.Status.PENDING_PAYMENT,
        Order.Status.PAID,
        Order.Status.PROCESSING,
    )

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        normalized_actor_type = _validate_public_actor(
            order=locked_order,
            to_status=Order.Status.CANCELLED,
            actor_type=actor_type,
            actor_user=actor_user,
        )

        if locked_order.status == Order.Status.CANCELLED:
            matching_sources = (
                (normalized_expected_status,)
                if normalized_expected_status is not None
                else cancellable_statuses
            )
            if OrderStatusHistory.objects.filter(
                order=locked_order,
                from_status__in=matching_sources,
                to_status=Order.Status.CANCELLED,
                actor_type=normalized_actor_type,
                actor_user=actor_user,
            ).exists():
                return OrderTransitionResult(order=locked_order, changed=False)
            raise InvalidOrderTransition(
                "The order was cancelled through a different command."
            )

        if (
            normalized_expected_status is not None
            and locked_order.status != normalized_expected_status
        ):
            raise InvalidOrderTransition(
                "Expected order status "
                f"{normalized_expected_status}, found {locked_order.status}."
            )
        if locked_order.status not in cancellable_statuses:
            raise InvalidOrderTransition(
                f"Order cannot transition from {locked_order.status} to "
                f"{Order.Status.CANCELLED}."
            )

        cancellation_time = at or timezone.now()
        source_status = locked_order.status
        _lock_order_payment_attempts(locked_order)
        reservations = _lock_order_reservations(locked_order)
        products_with_quantities = (
            _lock_products_for_stock_restoration(locked_order)
            if source_status in (Order.Status.PAID, Order.Status.PROCESSING)
            else ()
        )

        _fail_pending_payment_attempts(
            order=locked_order,
            at=cancellation_time,
        )
        InventoryReservation.objects.filter(
            pk__in=[reservation.pk for reservation in reservations],
            status=InventoryReservation.Status.ACTIVE,
        ).update(
            status=InventoryReservation.Status.RELEASED,
            updated_at=cancellation_time,
        )
        for product, quantity in products_with_quantities:
            product.stock_quantity += quantity
            product.save(update_fields=("stock_quantity", "updated_at"))

        return _apply_locked_transition(
            order=locked_order,
            from_status=source_status,
            to_status=Order.Status.CANCELLED,
            actor_type=normalized_actor_type,
            actor_user=actor_user,
            at=cancellation_time,
        )


def _mark_locked_order_paid(*, order, at):
    """Record payment finalization after its aggregate rows have been locked."""
    return _apply_locked_system_transition(
        order=order,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.PAID,
        at=at,
    )


def _mark_locked_order_expired(*, order, at):
    """Record expiry after its payment and reservation effects are applied."""
    return _apply_locked_system_transition(
        order=order,
        from_status=Order.Status.PENDING_PAYMENT,
        to_status=Order.Status.EXPIRED,
        at=at,
    )


def _apply_locked_system_transition(*, order, from_status, to_status, at):
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("A locked order transition requires an atomic transaction.")
    if order.status != from_status:
        raise InvalidOrderTransition(
            f"Expected order status {from_status}, found {order.status}."
        )
    return _apply_locked_transition(
        order=order,
        from_status=from_status,
        to_status=to_status,
        actor_type=OrderStatusHistory.ActorType.SYSTEM,
        actor_user=None,
        at=at,
    )


def _apply_locked_transition(
    *,
    order,
    from_status,
    to_status,
    actor_type,
    actor_user,
    at=None,
):
    transition_time = at or timezone.now()
    order.status = to_status
    update_fields = ["status", "updated_at"]

    timestamp_field = _STATUS_TIMESTAMP_FIELDS.get(to_status)
    if timestamp_field is not None:
        setattr(order, timestamp_field, transition_time)
        update_fields.append(timestamp_field)

    if to_status == Order.Status.CANCELLED:
        order.refund_status = (
            Order.RefundStatus.NOT_REQUIRED
            if from_status == Order.Status.PENDING_PAYMENT
            else Order.RefundStatus.REQUIRED
        )
        order.refund_resolved_at = None
        order.refund_resolved_by = None
        update_fields.extend(
            ("refund_status", "refund_resolved_at", "refund_resolved_by")
        )

    order.save(update_fields=update_fields)
    OrderStatusHistory.objects.create(
        order=order,
        from_status=from_status,
        to_status=to_status,
        actor_type=actor_type,
        actor_user=actor_user,
        created_at=transition_time,
    )
    return OrderTransitionResult(order=order, changed=True)


def resolve_order_refund(*, order, operator, at=None):
    """Record manual completion of the refund required by a paid cancellation."""
    _validate_operator(operator)
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.refund_status == Order.RefundStatus.RESOLVED:
            if locked_order.refund_resolved_by_id == operator.pk:
                return OrderTransitionResult(order=locked_order, changed=False)
            raise RefundResolutionError(
                "The refund was resolved through a different command."
            )
        if (
            locked_order.status != Order.Status.CANCELLED
            or locked_order.refund_status != Order.RefundStatus.REQUIRED
        ):
            raise RefundResolutionError("The order does not require a refund.")

        locked_order.refund_status = Order.RefundStatus.RESOLVED
        locked_order.refund_resolved_at = at or timezone.now()
        locked_order.refund_resolved_by = operator
        locked_order.save(
            update_fields=(
                "refund_status",
                "refund_resolved_at",
                "refund_resolved_by",
                "updated_at",
            )
        )
        return OrderTransitionResult(order=locked_order, changed=True)


def _lock_order_payment_attempts(order):
    from apps.payments.models import PaymentAttempt

    return list(
        PaymentAttempt.objects.select_for_update().filter(order=order).order_by("pk")
    )


def _lock_order_reservations(order):
    return list(
        InventoryReservation.objects.select_for_update()
        .filter(order=order)
        .order_by("pk")
    )


def _lock_products_for_stock_restoration(order):
    quantities = dict(
        OrderItem.objects.filter(order=order)
        .values("product_id")
        .annotate(quantity=Sum("quantity"))
        .values_list("product_id", "quantity")
    )
    if None in quantities:
        raise OrderCancellationInventoryInvalid(
            "The order inventory can no longer be restored."
        )

    products = list(
        Product.objects.select_for_update().filter(pk__in=quantities).order_by("pk")
    )
    if len(products) != len(quantities):
        raise OrderCancellationInventoryInvalid(
            "The order inventory can no longer be restored."
        )
    return tuple((product, quantities[product.pk]) for product in products)


def _fail_pending_payment_attempts(*, order, at):
    from apps.payments.models import PaymentAttempt

    PaymentAttempt.objects.filter(
        order=order,
        status=PaymentAttempt.Status.PENDING,
    ).update(status=PaymentAttempt.Status.FAILED, updated_at=at)


def _prepare_locked_fulfillment_transition(*, order, to_status):
    if to_status == Order.Status.PROCESSING:
        Shipment.objects.get_or_create(order=order)
        return
    if to_status not in (Order.Status.SHIPPED, Order.Status.DELIVERED):
        return

    try:
        shipment = Shipment.objects.select_for_update().get(order=order)
    except Shipment.DoesNotExist as exc:
        raise ShipmentDetailsRequired(
            "The order does not have a shipment record."
        ) from exc
    if to_status == Order.Status.SHIPPED and (
        not shipment.carrier.strip() or not shipment.tracking_number.strip()
    ):
        raise ShipmentDetailsRequired(
            "Carrier and tracking number are required before shipping."
        )


def _matching_transition_exists(
    *,
    order,
    from_status,
    to_status,
    actor_type,
    actor_user,
):
    return OrderStatusHistory.objects.filter(
        order=order,
        from_status=from_status,
        to_status=to_status,
        actor_type=actor_type,
        actor_user=actor_user,
    ).exists()


def _normalize_status(status):
    try:
        return Order.Status(status)
    except ValueError as exc:
        raise InvalidOrderTransition(f"Unknown order status: {status}.") from exc


def _validate_public_actor(*, order, to_status, actor_type, actor_user):
    try:
        normalized_actor_type = OrderStatusHistory.ActorType(actor_type)
    except ValueError as exc:
        raise InvalidOrderTransitionActor(
            "Unknown order transition actor type."
        ) from exc

    if normalized_actor_type not in _PUBLIC_ACTORS_BY_TARGET[to_status]:
        raise InvalidOrderTransitionActor(
            f"{normalized_actor_type} cannot perform the {to_status} command."
        )
    if actor_user is None or actor_user.pk is None:
        raise InvalidOrderTransitionActor(
            "Customer and operator transitions require a persisted user."
        )
    if normalized_actor_type == OrderStatusHistory.ActorType.CUSTOMER:
        if not order.customer.__class__.objects.filter(
            pk=order.customer_id,
            user_id=actor_user.pk,
        ).exists():
            raise InvalidOrderTransitionActor(
                "Customer transitions must be attributed to the order owner."
            )
    else:
        _validate_operator(actor_user)
    return normalized_actor_type


def _validate_operator(user):
    if user is None or user.pk is None or not user.is_staff:
        raise InvalidOrderTransitionActor(
            "Operator transitions require a persisted staff user."
        )
