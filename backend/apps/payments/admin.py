from django.contrib import admin
from django.db.models import Count, F, Min, Q
from django.utils import timezone

from apps.orders.models import InventoryReservation, Order

from .bale_webhooks import PROCESSING_LEASE
from .models import BaleWebhookUpdate, PaymentAttempt


class PaymentOperationalStateFilter(admin.SimpleListFilter):
    title = "وضعیت عملیاتی"
    parameter_name = "payment_state"

    def lookups(self, request, model_admin):
        return (
            ("failed_pending", "ناموفق در زمان انتظار سفارش"),
            ("payment_elapsed", "در انتظار؛ مهلت پرداخت پایان یافته"),
            ("payment_inventory", "در انتظار؛ موجودی پرداخت نامعتبر"),
            ("refund_required", "موفق؛ نیازمند بازپرداخت"),
            ("inconsistent", "ناسازگار با سفارش"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "failed_pending":
            return queryset.filter(
                status=PaymentAttempt.Status.FAILED,
                order__status=Order.Status.PENDING_PAYMENT,
            )
        if value == "payment_elapsed":
            return queryset.filter(
                status=PaymentAttempt.Status.PENDING,
                order__status=Order.Status.PENDING_PAYMENT,
                admin_active_reservation_count=F("admin_reservation_count"),
                admin_payment_expires_at__lte=timezone.now(),
            ).exclude(admin_reservation_count=0)
        if value == "payment_inventory":
            return queryset.filter(
                status=PaymentAttempt.Status.PENDING,
                order__status=Order.Status.PENDING_PAYMENT,
            ).filter(
                Q(admin_reservation_count=0)
                | ~Q(admin_active_reservation_count=F("admin_reservation_count"))
            )
        if value == "refund_required":
            return queryset.filter(
                status=PaymentAttempt.Status.SUCCESS,
                order__refund_status=Order.RefundStatus.REQUIRED,
            )
        if value == "inconsistent":
            return queryset.filter(
                Q(status=PaymentAttempt.Status.PENDING)
                & ~Q(order__status=Order.Status.PENDING_PAYMENT)
                | Q(
                    status=PaymentAttempt.Status.SUCCESS,
                    order__status=Order.Status.PENDING_PAYMENT,
                )
                | Q(
                    status=PaymentAttempt.Status.SUCCESS,
                    order__status=Order.Status.EXPIRED,
                    order__refund_status=Order.RefundStatus.NOT_REQUIRED,
                )
                | Q(
                    status=PaymentAttempt.Status.SUCCESS,
                    order__status=Order.Status.CANCELLED,
                    order__refund_status=Order.RefundStatus.NOT_REQUIRED,
                )
            )
        return queryset


class BaleWebhookOperationalStateFilter(admin.SimpleListFilter):
    title = "وضعیت عملیاتی"
    parameter_name = "webhook_state"

    def lookups(self, request, model_admin):
        return (
            ("recoverable", "قابل بازیابی محلی"),
            ("rejected", "ردشده"),
            ("processing", "در حال پردازش"),
            ("invalid_processing", "در حال پردازش بدون زمان دریافت"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        stale_before = timezone.now() - PROCESSING_LEASE
        if value == "recoverable":
            return queryset.filter(
                Q(status=BaleWebhookUpdate.Status.PENDING)
                | Q(
                    status=BaleWebhookUpdate.Status.PROCESSING,
                    processing_started_at__lte=stale_before,
                )
            )
        if value == "rejected":
            return queryset.filter(status=BaleWebhookUpdate.Status.REJECTED)
        if value == "processing":
            return queryset.filter(
                status=BaleWebhookUpdate.Status.PROCESSING,
                processing_started_at__gt=stale_before,
            )
        if value == "invalid_processing":
            return queryset.filter(
                status=BaleWebhookUpdate.Status.PROCESSING,
                processing_started_at__isnull=True,
            )
        return queryset


class ReadOnlyPaymentAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(ReadOnlyPaymentAdmin):
    list_display = (
        "id",
        "order",
        "customer_email",
        "status",
        "operational_state",
        "order_status",
        "amount",
        "currency",
        "gateway",
        "created_at",
        "updated_at",
    )
    list_filter = (
        PaymentOperationalStateFilter,
        "status",
        "order__status",
        "gateway",
        "currency",
        "created_at",
    )
    search_fields = ("=id", "=order__id", "order__customer__user__email")
    list_select_related = ("order", "order__customer", "order__customer__user")
    ordering = ("-created_at", "-pk")
    fields = (
        "id",
        "order",
        "status",
        "amount",
        "currency",
        "gateway",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields
    date_hierarchy = "created_at"
    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                admin_reservation_count=Count(
                    "order__inventory_reservations",
                    distinct=True,
                ),
                admin_active_reservation_count=Count(
                    "order__inventory_reservations",
                    filter=Q(
                        order__inventory_reservations__status=(
                            InventoryReservation.Status.ACTIVE
                        )
                    ),
                    distinct=True,
                ),
                admin_payment_expires_at=Min(
                    "order__inventory_reservations__expires_at",
                    filter=Q(
                        order__inventory_reservations__status=(
                            InventoryReservation.Status.ACTIVE
                        )
                    ),
                ),
            )
        )

    @admin.display(description="مشتری", ordering="order__customer__user__email")
    def customer_email(self, obj):
        return obj.order.customer.user.email

    @admin.display(description="وضعیت سفارش", ordering="order__status")
    def order_status(self, obj):
        return obj.order.status

    @admin.display(description="وضعیت عملیاتی")
    def operational_state(self, obj):
        if (
            (
                obj.status == PaymentAttempt.Status.PENDING
                and obj.order.status != Order.Status.PENDING_PAYMENT
            )
            or (
                obj.status == PaymentAttempt.Status.SUCCESS
                and obj.order.status == Order.Status.PENDING_PAYMENT
            )
            or (
                obj.status == PaymentAttempt.Status.SUCCESS
                and obj.order.status == Order.Status.EXPIRED
                and obj.order.refund_status == Order.RefundStatus.NOT_REQUIRED
            )
            or (
                obj.status == PaymentAttempt.Status.SUCCESS
                and obj.order.status == Order.Status.CANCELLED
                and obj.order.refund_status == Order.RefundStatus.NOT_REQUIRED
            )
        ):
            return "نیازمند بررسی؛ ناسازگار با سفارش"
        if (
            obj.status == PaymentAttempt.Status.SUCCESS
            and obj.order.refund_status == Order.RefundStatus.REQUIRED
        ):
            return "نیازمند بازپرداخت"
        if obj.status == PaymentAttempt.Status.FAILED:
            if obj.order.status == Order.Status.PENDING_PAYMENT:
                return "ناموفق در زمان انتظار سفارش"
            return "ناموفق؛ سابقه تاریخی"
        if obj.status == PaymentAttempt.Status.PENDING:
            if (
                obj.admin_reservation_count == 0
                or obj.admin_active_reservation_count != obj.admin_reservation_count
            ):
                return "موجودی پرداخت نامعتبر است"
            if (
                obj.admin_payment_expires_at is not None
                and obj.admin_payment_expires_at <= timezone.now()
            ):
                return "مهلت پرداخت پایان یافته"
            return "در انتظار پرداخت"
        return "تکمیل‌شده"


@admin.register(BaleWebhookUpdate)
class BaleWebhookUpdateAdmin(ReadOnlyPaymentAdmin):
    list_display = (
        "update_id",
        "event_type",
        "status",
        "operational_state",
        "payment_attempt",
        "amount",
        "currency",
        "received_at",
        "processed_at",
    )
    list_filter = (
        BaleWebhookOperationalStateFilter,
        "event_type",
        "status",
        "currency",
        "received_at",
    )
    search_fields = (
        "=update_id",
        "=payment_attempt__id",
        "=payment_attempt__order__id",
    )
    list_select_related = ("payment_attempt", "payment_attempt__order")
    ordering = ("-received_at", "-pk")
    fields = (
        "update_id",
        "event_type",
        "status",
        "payment_attempt",
        "amount",
        "currency",
        "received_at",
        "processing_started_at",
        "processed_at",
    )
    readonly_fields = fields
    date_hierarchy = "received_at"
    list_per_page = 50

    @admin.display(description="وضعیت عملیاتی")
    def operational_state(self, obj):
        if obj.status == BaleWebhookUpdate.Status.PENDING:
            return "قابل بازیابی محلی"
        if obj.status == BaleWebhookUpdate.Status.PROCESSING:
            if obj.processing_started_at is None:
                return "نیازمند بررسی؛ زمان شروع پردازش ثبت نشده"
            if obj.processing_started_at <= timezone.now() - PROCESSING_LEASE:
                return "متوقف‌شده؛ قابل بازیابی محلی"
            return "در حال پردازش"
        if obj.status == BaleWebhookUpdate.Status.REJECTED:
            return "ردشده"
        return "پردازش‌شده"
