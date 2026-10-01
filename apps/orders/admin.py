from django import forms
from django.contrib import admin, messages

from .lifecycle import OrderLifecycleError, transition_order
from .models import Order, OrderStatusHistory, Shipment


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
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "refund_status")
    search_fields = ("id", "customer__user__email")
    list_select_related = ("customer", "customer__user")
    ordering = ("-created_at", "-pk")
    readonly_fields = tuple(field.name for field in Order._meta.fields)
    actions = ("mark_processing", "mark_shipped", "mark_delivered")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Mark selected orders as processing")
    def mark_processing(self, request, queryset):
        self._transition_selected_orders(
            request=request,
            queryset=queryset,
            from_status=Order.Status.PAID,
            to_status=Order.Status.PROCESSING,
        )

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        self._transition_selected_orders(
            request=request,
            queryset=queryset,
            from_status=Order.Status.PROCESSING,
            to_status=Order.Status.SHIPPED,
        )

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        self._transition_selected_orders(
            request=request,
            queryset=queryset,
            from_status=Order.Status.SHIPPED,
            to_status=Order.Status.DELIVERED,
        )

    def _transition_selected_orders(
        self,
        *,
        request,
        queryset,
        from_status,
        to_status,
    ):
        changed = 0
        unchanged = 0
        failed = 0
        for order in queryset.order_by("pk"):
            try:
                result = transition_order(
                    order=order,
                    from_status=from_status,
                    to_status=to_status,
                    actor_type=OrderStatusHistory.ActorType.OPERATOR,
                    actor_user=request.user,
                )
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
                f"{changed} order(s) marked as {to_status}.",
                level=messages.SUCCESS,
            )
        if unchanged:
            self.message_user(
                request,
                f"{unchanged} order(s) were already {to_status} by this operator.",
                level=messages.INFO,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} order(s) could not be marked as {to_status}.",
                level=messages.WARNING,
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
