from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html

from .models import Category, Product, ProductImage


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
            raise ValidationError("Select only one new primary image.")

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

    @admin.display(description="Preview")
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
        ("Category", {"fields": ("name", "slug", "parent", "is_active")}),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    list_per_page = 50
    save_on_top = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
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
            "Product",
            {"fields": ("name", "slug", "sku", "category", "status")},
        ),
        ("Catalog", {"fields": ("description", "price")}),
        ("Inventory", {"fields": ("stock_quantity",)}),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    inlines = (ProductImageInline,)
    list_per_page = 50
    save_on_top = True

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

    @admin.display(description="Primary image")
    def primary_image_thumbnail(self, obj):
        images = getattr(obj, "admin_primary_images", ())
        if not images:
            return "—"
        image = images[0]
        return image_thumbnail(image.image, alt_text=image.alt_text)

    @admin.display(boolean=True, description="In stock")
    def in_stock(self, obj):
        return obj.stock_quantity > 0
