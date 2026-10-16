from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Min, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .lifecycle import (
    OrderLifecycleError,
    cancel_order,
    resolve_order_refund,
    transition_order,
)
from .models import (
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatusHistory,
    Shipment,
)


class ReadOnlyOrderInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OrderItemInline(ReadOnlyOrderInline):
    model = OrderItem
    fields = ("product_name", "sku", "unit_price", "quantity", "line_total")
    readonly_fields = fields
    ordering = ("pk",)


class InventoryReservationInline(ReadOnlyOrderInline):
    model = InventoryReservation
    fields = ("product", "quantity", "status", "expires_at", "created_at")
    readonly_fields = fields
    ordering = ("pk",)


class OrderStatusHistoryInline(ReadOnlyOrderInline):
    model = OrderStatusHistory
    fields = (
        "from_status",
        "to_status",
        "actor_type",
        "actor_user",
        "created_at",
    )
    readonly_fields = fields
    ordering = ("created_at", "pk")


class OrderOperationalStateFilter(admin.SimpleListFilter):
    title = "نیاز به رسیدگی اپراتور"
    parameter_name = "operational_state"

    def lookups(self, request, model_admin):
        return (
            ("attention", "همه موارد نیازمند رسیدگی"),
            ("refund", "نیازمند بازپرداخت"),
            ("payment_elapsed", "مهلت پرداخت پایان یافته"),
            ("payment_inventory", "موجودی نامعتبر پرداخت"),
            ("start_processing", "آماده پردازش"),
            ("shipment_details", "نیازمند اطلاعات مرسوله"),
            ("ready_to_ship", "آماده ارسال"),
            ("awaiting_delivery", "در انتظار تأیید تحویل"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "refund":
            return queryset.filter(refund_status=Order.RefundStatus.REQUIRED)
        if value == "payment_elapsed":
            return queryset.filter(
                status=Order.Status.PENDING_PAYMENT,
                admin_active_reservation_count=F("admin_reservation_count"),
                admin_payment_expires_at__lte=timezone.now(),
            ).exclude(admin_reservation_count=0)
        if value == "payment_inventory":
            return queryset.filter(status=Order.Status.PENDING_PAYMENT).filter(
                Q(admin_reservation_count=0)
                | ~Q(admin_active_reservation_count=F("admin_reservation_count"))
            )
        if value == "start_processing":
            return queryset.filter(status=Order.Status.PAID)
        if value == "shipment_details":
            return queryset.filter(status=Order.Status.PROCESSING).filter(
                Q(shipment__isnull=True)
                | Q(shipment__carrier="")
                | Q(shipment__tracking_number="")
            )
        if value == "ready_to_ship":
            return (
                queryset.filter(status=Order.Status.PROCESSING)
                .exclude(shipment__isnull=True)
                .exclude(shipment__carrier="")
                .exclude(shipment__tracking_number="")
            )
        if value == "awaiting_delivery":
            return queryset.filter(status=Order.Status.SHIPPED)
        if value == "attention":
            return queryset.filter(
                Q(refund_status=Order.RefundStatus.REQUIRED)
                | Q(status__in=(Order.Status.PAID, Order.Status.PROCESSING))
                | Q(status=Order.Status.SHIPPED)
                | Q(
                    status=Order.Status.PENDING_PAYMENT,
                    admin_payment_expires_at__lte=timezone.now(),
                )
                | Q(
                    status=Order.Status.PENDING_PAYMENT,
                    admin_reservation_count=0,
                )
                | Q(
                    status=Order.Status.PENDING_PAYMENT,
                    admin_active_reservation_count__lt=F("admin_reservation_count"),
                )
            )
        return queryset


class ShipmentOperationalStateFilter(admin.SimpleListFilter):
    title = "وضعیت تکمیل سفارش"
    parameter_name = "shipment_state"

    def lookups(self, request, model_admin):
        return (
            ("needs_details", "نیازمند اطلاعات مرسوله"),
            ("ready_to_ship", "آماده ارسال"),
            ("shipped", "در مسیر ارسال"),
            ("delivered", "تحویل‌شده"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "needs_details":
            return queryset.filter(order__status=Order.Status.PROCESSING).filter(
                Q(carrier="") | Q(tracking_number="")
            )
        if value == "ready_to_ship":
            return (
                queryset.filter(order__status=Order.Status.PROCESSING)
                .exclude(carrier="")
                .exclude(tracking_number="")
            )
        if value == "shipped":
            return queryset.filter(order__status=Order.Status.SHIPPED)
        if value == "delivered":
            return queryset.filter(order__status=Order.Status.DELIVERED)
        return queryset


class ShipmentAdminForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ("carrier", "tracking_number")

    def clean(self):
        cleaned_data = super().clean()
        carrier = cleaned_data.get("carrier", "").strip()
        tracking_number = cleaned_data.get("tracking_number", "").strip()
        if not carrier or not tracking_number:
            raise forms.ValidationError("حامل و کد رهگیری مرسوله الزامی هستند.")
        cleaned_data["carrier"] = carrier
        cleaned_data["tracking_number"] = tracking_number
        return cleaned_data


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "status",
        "operator_state",
        "refund_status",
        "grand_total",
        "payment_attempts_link",
        "created_at",
    )
    list_filter = (
        OrderOperationalStateFilter,
        "status",
        "refund_status",
        "created_at",
    )
    search_fields = (
        "=id",
        "customer__user__email",
        "shipping_recipient_first_name",
        "shipping_recipient_last_name",
        "shipping_recipient_phone_number",
        "shipping_postal_code",
    )
    list_select_related = ("customer", "customer__user")
    ordering = ("-created_at", "-pk")
    readonly_fields = tuple(field.name for field in Order._meta.fields) + (
        "payment_attempts_link",
    )
    actions = (
        "mark_processing",
        "mark_shipped",
        "mark_delivered",
        "cancel_orders",
        "resolve_refunds",
    )
    inlines = (
        OrderItemInline,
        InventoryReservationInline,
        OrderStatusHistoryInline,
    )
    date_hierarchy = "created_at"
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("shipment")
            .annotate(
                admin_payment_attempt_count=Count(
                    "payment_attempts",
                    distinct=True,
                ),
                admin_reservation_count=Count(
                    "inventory_reservations",
                    distinct=True,
                ),
                admin_active_reservation_count=Count(
                    "inventory_reservations",
                    filter=Q(
                        inventory_reservations__status=(
                            InventoryReservation.Status.ACTIVE
                        )
                    ),
                    distinct=True,
                ),
                admin_payment_expires_at=Min(
                    "inventory_reservations__expires_at",
                    filter=Q(
                        inventory_reservations__status=(
                            InventoryReservation.Status.ACTIVE
                        )
                    ),
                ),
            )
        )

    @admin.display(description="وضعیت عملیاتی")
    def operator_state(self, obj):
        if obj.refund_status == Order.RefundStatus.REQUIRED:
            return "نیازمند بازپرداخت"
        if obj.status == Order.Status.PENDING_PAYMENT:
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
        if obj.status == Order.Status.PAID:
            return "آماده پردازش"
        if obj.status == Order.Status.PROCESSING:
            shipment = getattr(obj, "shipment", None)
            if shipment is None or not shipment.carrier or not shipment.tracking_number:
                return "نیازمند اطلاعات مرسوله"
            return "آماده ارسال"
        if obj.status == Order.Status.SHIPPED:
            return "در انتظار تأیید تحویل"
        return "—"

    @admin.action(
        description="انتقال سفارش‌های انتخاب‌شده به «در حال پردازش»",
        permissions=("change",),
    )
    def mark_processing(self, request, queryset):
        self._transition_selected_orders(
            request=request,
            queryset=queryset,
            from_status=Order.Status.PAID,
            to_status=Order.Status.PROCESSING,
        )

    @admin.action(
        description="ثبت ارسال سفارش‌های انتخاب‌شده",
        permissions=("change",),
    )
    def mark_shipped(self, request, queryset):
        self._transition_selected_orders(
            request=request,
            queryset=queryset,
            from_status=Order.Status.PROCESSING,
            to_status=Order.Status.SHIPPED,
        )

    @admin.action(
        description="ثبت تحویل سفارش‌های انتخاب‌شده",
        permissions=("change",),
    )
    def mark_delivered(self, request, queryset):
        self._transition_selected_orders(
            request=request,
            queryset=queryset,
            from_status=Order.Status.SHIPPED,
            to_status=Order.Status.DELIVERED,
        )

    @admin.action(
        description="لغو سفارش‌های مجاز انتخاب‌شده",
        permissions=("change",),
    )
    def cancel_orders(self, request, queryset):
        self._run_order_command(
            request=request,
            queryset=queryset,
            command=lambda order: cancel_order(
                order=order,
                actor_type=OrderStatusHistory.ActorType.OPERATOR,
                actor_user=request.user,
            ),
            success_message="لغو شد",
        )

    @admin.action(
        description="ثبت انجام بازپرداخت سفارش‌های انتخاب‌شده",
        permissions=("change",),
    )
    def resolve_refunds(self, request, queryset):
        self._run_order_command(
            request=request,
            queryset=queryset,
            command=lambda order: resolve_order_refund(
                order=order,
                operator=request.user,
            ),
            success_message="با بازپرداخت انجام‌شده ثبت شد",
        )

    def _transition_selected_orders(
        self,
        *,
        request,
        queryset,
        from_status,
        to_status,
    ):
        self._run_order_command(
            request=request,
            queryset=queryset,
            command=lambda order: transition_order(
                order=order,
                from_status=from_status,
                to_status=to_status,
                actor_type=OrderStatusHistory.ActorType.OPERATOR,
                actor_user=request.user,
            ),
            success_message="به وضعیت جدید منتقل شد",
        )

    def _run_order_command(self, *, request, queryset, command, success_message):
        if not self.has_change_permission(request):
            raise PermissionDenied

        changed = 0
        unchanged = 0
        failed = 0
        for order in queryset.order_by("pk"):
            try:
                result = command(order)
            except OrderLifecycleError as exc:
                failed += 1
                self.message_user(
                    request,
                    f"سفارش {order.pk}: {exc}",
                    level=messages.ERROR,
                )
            else:
                if result.changed:
                    changed += 1
                else:
                    unchanged += 1

        if changed:
            self.message_user(
                request,
                f"عملیات روی {changed} سفارش انجام شد: {success_message}.",
                level=messages.SUCCESS,
            )
        if unchanged:
            self.message_user(
                request,
                f"عملیات {unchanged} سفارش قبلاً توسط همین اپراتور انجام شده بود.",
                level=messages.INFO,
            )
        if failed:
            self.message_user(
                request,
                f"عملیات {failed} سفارش قابل انجام نبود.",
                level=messages.WARNING,
            )

    @admin.display(description="پرداخت‌ها")
    def payment_attempts_link(self, obj):
        url = reverse("admin:payments_paymentattempt_changelist")
        return format_html(
            '<a href="{}?order__id__exact={}">{} تلاش پرداخت</a>',
            url,
            obj.pk,
            obj.admin_payment_attempt_count,
        )


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    form = ShipmentAdminForm
    list_display = (
        "order",
        "carrier",
        "tracking_number",
        "order_status",
        "fulfillment_state",
        "updated_at",
    )
    search_fields = (
        "order__id",
        "order__customer__user__email",
        "carrier",
        "tracking_number",
    )
    list_select_related = ("order", "order__customer", "order__customer__user")
    ordering = ("-created_at", "-pk")
    list_filter = (ShipmentOperationalStateFilter, "order__status", "carrier")
    date_hierarchy = "created_at"
    list_per_page = 50
    fields = (
        "order",
        "carrier",
        "tracking_number",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if obj is not None and obj.order.status != Order.Status.PROCESSING:
            return False
        return allowed

    def get_readonly_fields(self, request, obj=None):
        readonly = ("order", "created_at", "updated_at")
        if obj is None or obj.order.status != Order.Status.PROCESSING:
            return readonly + ("carrier", "tracking_number")
        return readonly

    @admin.display(description="وضعیت سفارش", ordering="order__status")
    def order_status(self, obj):
        return obj.order.status

    @admin.display(description="وضعیت تکمیل سفارش")
    def fulfillment_state(self, obj):
        if obj.order.status == Order.Status.PROCESSING:
            if not obj.carrier or not obj.tracking_number:
                return "نیازمند اطلاعات مرسوله"
            return "آماده ارسال"
        if obj.order.status == Order.Status.SHIPPED:
            return "در مسیر ارسال"
        if obj.order.status == Order.Status.DELIVERED:
            return "تحویل‌شده"
        if obj.order.status == Order.Status.CANCELLED:
            return "لغوشده"
        return "—"
