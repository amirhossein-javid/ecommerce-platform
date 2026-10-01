from django.contrib import admin

from .models import BaleWebhookUpdate, PaymentAttempt


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
        "amount",
        "currency",
        "gateway",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "gateway", "currency", "created_at")
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

    @admin.display(description="Customer", ordering="order__customer__user__email")
    def customer_email(self, obj):
        return obj.order.customer.user.email


@admin.register(BaleWebhookUpdate)
class BaleWebhookUpdateAdmin(ReadOnlyPaymentAdmin):
    list_display = (
        "update_id",
        "event_type",
        "status",
        "payment_attempt",
        "amount",
        "currency",
        "received_at",
        "processed_at",
    )
    list_filter = ("event_type", "status", "currency", "received_at")
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
