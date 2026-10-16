from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import router, transaction
from django.db.models import Prefetch, Sum
from django.forms.models import BaseInlineFormSet
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Category,
    Product,
    ProductImage,
    ProductReview,
    ProductReviewReply,
    lock_category_parent_structure,
)


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

    def clean_stock_quantity(self):
        stock_quantity = self.cleaned_data["stock_quantity"]
        if self.instance.pk is None:
            return stock_quantity

        reserved_quantity = self.instance.inventory_reservations.filter(
            status="ACTIVE",
            expires_at__gt=timezone.now(),
        ).aggregate(total=Sum("quantity", default=0))["total"]
        if stock_quantity < reserved_quantity:
            raise ValidationError(
                "موجودی نمی‌تواند از تعداد رزروشده فعال کمتر باشد "
                f"({reserved_quantity})."
            )
        return stock_quantity


def image_thumbnail(image, *, alt_text="", size=56):
    if not image:
        return "—"
    return format_html(
        '<img src="{}" alt="{}" width="{}" height="{}" style="object-fit: contain;" />',
        image.url,
        alt_text,
        size,
        size,
    )


class ProductImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        newly_selected_primary_forms = [
            form
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE", False)
            and form.cleaned_data.get("is_primary", False)
            and not form.initial.get("is_primary", False)
        ]
        if len(newly_selected_primary_forms) > 1:
            raise ValidationError("فقط یک تصویر اصلی جدید انتخاب کنید.")

    def save(self, commit=True):
        if not commit or self.instance.pk is None:
            return super().save(commit=commit)

        with transaction.atomic():
            Product.objects.select_for_update().get(pk=self.instance.pk)
            saved_instances = super().save(commit=True)
            images = ProductImage.objects.filter(product=self.instance)
            if images.exists() and not images.filter(is_primary=True).exists():
                replacement = images.order_by("position", "pk").first()
                ProductImage.objects.filter(pk=replacement.pk).update(is_primary=True)
            return saved_instances


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    formset = ProductImageInlineFormSet
    extra = 1
    fields = (
        "preview",
        "image",
        "alt_text",
        "position",
        "is_primary",
        "created_at",
    )
    readonly_fields = ("preview", "created_at")
    ordering = ("position", "pk")

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if obj is None:
            return "—"
        return image_thumbnail(obj.image, alt_text=obj.alt_text)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "parent", "is_active")
    list_display_links = ("id", "name")
    list_editable = ("is_active",)
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("name", "pk")
    list_select_related = ("parent",)
    autocomplete_fields = ("parent",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("دسته‌بندی", {"fields": ("name", "slug", "parent", "is_active")}),
        (
            "اطلاعات سیستمی",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    list_per_page = 50
    save_on_top = True

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.method != "POST":
            return super().changeform_view(
                request,
                object_id=object_id,
                form_url=form_url,
                extra_context=extra_context,
            )

        using = router.db_for_write(self.model)
        with transaction.atomic(using=using):
            lock_category_parent_structure(using=using)
            return super().changeform_view(
                request,
                object_id=object_id,
                form_url=form_url,
                extra_context=extra_context,
            )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = (
        "name",
        "primary_image_thumbnail",
        "category",
        "price",
        "stock_quantity",
        "in_stock",
        "status",
        "sku",
    )
    list_display_links = ("name",)
    list_editable = ("status",)
    list_filter = ("status", "category")
    search_fields = ("name", "sku", "slug")
    ordering = ("-created_at", "pk")
    list_select_related = ("category",)
    autocomplete_fields = ("category",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "محصول",
            {"fields": ("name", "slug", "sku", "category", "status")},
        ),
        ("کاتالوگ", {"fields": ("description", "price")}),
        ("موجودی", {"fields": ("stock_quantity",)}),
        (
            "اطلاعات سیستمی",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    inlines = (ProductImageInline,)
    list_per_page = 50
    save_on_top = True

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        with transaction.atomic():
            if request.method == "POST" and object_id is not None:
                Product.objects.select_for_update().filter(pk=object_id).first()
            return super().changeform_view(
                request,
                object_id=object_id,
                form_url=form_url,
                extra_context=extra_context,
            )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.filter(is_primary=True),
                    to_attr="admin_primary_images",
                )
            )
        )

    @admin.display(description="تصویر اصلی")
    def primary_image_thumbnail(self, obj):
        images = getattr(obj, "admin_primary_images", ())
        if not images:
            return "—"
        image = images[0]
        return image_thumbnail(image.image, alt_text=image.alt_text)

    @admin.display(boolean=True, description="دارای موجودی")
    def in_stock(self, obj):
        return obj.stock_quantity > 0


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "customer",
        "rating",
        "status",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    list_filter = (
        "status",
        ("product", admin.RelatedOnlyFieldListFilter),
        "rating",
        "created_at",
    )
    search_fields = (
        "product__name",
        "product__slug",
        "customer__user__email",
        "customer__first_name",
        "customer__last_name",
        "comment",
    )
    list_select_related = ("product", "customer", "customer__user")
    ordering = ("-created_at", "-pk")
    fields = (
        "product",
        "customer_display_name",
        "rating",
        "comment",
        "status",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields
    actions = ("approve_reviews", "reject_reviews")
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

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(
            request,
            obj,
        ) or super().has_change_permission(request, obj)

    @admin.display(description="مشتری")
    def customer_display_name(self, obj):
        display_name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
        return display_name or f"مشتری شمارهٔ {obj.customer_id}"

    @admin.action(
        description="تأیید دیدگاه‌های در انتظار انتخاب‌شده",
        permissions=("change",),
    )
    def approve_reviews(self, request, queryset):
        self._moderate_pending(
            request=request,
            queryset=queryset,
            target_status=ProductReview.Status.APPROVED,
        )

    @admin.action(
        description="رد دیدگاه‌های در انتظار انتخاب‌شده",
        permissions=("change",),
    )
    def reject_reviews(self, request, queryset):
        self._moderate_pending(
            request=request,
            queryset=queryset,
            target_status=ProductReview.Status.REJECTED,
        )

    def _moderate_pending(self, *, request, queryset, target_status):
        if not self.has_change_permission(request):
            raise PermissionDenied

        with transaction.atomic():
            changed = queryset.filter(status=ProductReview.Status.PENDING).update(
                status=target_status,
                updated_at=timezone.now(),
            )
        skipped = queryset.count() - changed
        if changed:
            self.message_user(
                request,
                f"وضعیت {changed} دیدگاه در انتظار تغییر کرد.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} دیدگاه خارج از وضعیت انتظار بدون تغییر باقی ماند.",
                level=messages.WARNING,
            )


class ProductReviewReplyAdminForm(forms.ModelForm):
    class Meta:
        model = ProductReviewReply
        fields = ("review", "comment")

    def clean_comment(self):
        comment = self.cleaned_data["comment"].strip()
        if not comment:
            raise ValidationError("متن پاسخ نمی‌تواند خالی باشد.")
        return comment


@admin.register(ProductReviewReply)
class ProductReviewReplyAdmin(admin.ModelAdmin):
    form = ProductReviewReplyAdminForm
    list_display = ("id", "review", "created_at", "updated_at")
    list_display_links = ("id", "review")
    search_fields = (
        "review__product__name",
        "review__customer__first_name",
        "review__customer__last_name",
        "review__comment",
        "comment",
    )
    list_select_related = (
        "review",
        "review__product",
        "review__customer",
    )
    autocomplete_fields = ("review",)
    fields = ("review", "comment", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at", "-pk")

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ("review", *self.readonly_fields)
        return self.readonly_fields
