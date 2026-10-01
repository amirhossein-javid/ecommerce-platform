from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.urls import reverse
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


class ShipmentAdminForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ("carrier", "tracking_number")

    def clean(self):
        cleaned_data = super().clean()
        carrier = cleaned_data.get("carrier", "").strip()
        tracking_number = cleaned_data.get("tracking_number", "").strip()
        if not carrier or not tracking_number:
            raise forms.ValidationError(
                "Carrier and tracking number are required for shipment."
            )
        cleaned_data["carrier"] = carrier
        cleaned_data["tracking_number"] = tracking_number
        return cleaned_data


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "status",
        "refund_status",
        "grand_total",
        "payment_attempts_link",
        "created_at",
    )
    list_filter = ("status", "refund_status", "created_at")
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
            .annotate(admin_payment_attempt_count=Count("payment_attempts"))
        )

    @admin.action(
        description="Mark selected orders as processing",
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
        description="Mark selected orders as shipped",
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
        description="Mark selected orders as delivered",
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
        description="Cancel selected eligible orders",
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
            success_message="cancelled",
        )

    @admin.action(
        description="Mark selected required refunds as resolved",
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
            success_message="refund(s) resolved for",
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
            success_message=f"marked as {to_status}",
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
                    f"Order {order.pk}: {exc}",
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
                f"{changed} order(s) {success_message}.",
                level=messages.SUCCESS,
            )
        if unchanged:
            self.message_user(
                request,
                f"{unchanged} order command(s) were already completed by this "
                "operator.",
                level=messages.INFO,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} order command(s) could not be completed.",
                level=messages.WARNING,
            )

    @admin.display(description="Payments")
    def payment_attempts_link(self, obj):
        url = reverse("admin:payments_paymentattempt_changelist")
        return format_html(
            '<a href="{}?order__id__exact={}">{} attempt(s)</a>',
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
    list_filter = ("order__status", "carrier")
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

    @admin.display(description="Order status", ordering="order__status")
    def order_status(self, obj):
        return obj.order.status
