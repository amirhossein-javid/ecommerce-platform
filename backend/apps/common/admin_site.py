from django import forms
from django.contrib.admin import AdminSite, ModelAdmin, helpers
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .admin_presentation import localize_app_list, make_admin_list_display


class PersianAdminPresentationMixin:
    """Localize list presentation without changing model metadata or queries."""

    def get_list_display(self, request):
        editable_fields = set(self.list_editable)
        localized = []
        for field in super().get_list_display(request):
            replacement = (
                make_admin_list_display(self.model, field)
                if isinstance(field, str) and field not in editable_fields
                else None
            )
            localized.append(replacement or field)
        return tuple(localized)

    def action_checkbox(self, obj):
        attrs = {
            "class": "action-select",
            "aria-label": format_html(
                "انتخاب این مورد برای انجام عملیات — {}",
                str(obj),
            ),
        }
        checkbox = forms.CheckboxInput(attrs, lambda value: False)
        return checkbox.render(helpers.ACTION_CHECKBOX_NAME, str(obj.pk))

    action_checkbox.short_description = mark_safe(
        '<input type="checkbox" id="action-toggle" '
        'aria-label="انتخاب همه موارد این صفحه برای انجام عملیات">'
    )


class NaghshAdminSite(AdminSite):
    site_header = "مدیریت فروشگاه نقش‌جهان"
    site_title = "نقش‌جهان"
    index_title = "مرکز مدیریت فروشگاه"

    def register(self, model_or_iterable, admin_class=None, **options):
        admin_class = admin_class or ModelAdmin
        if not issubclass(admin_class, PersianAdminPresentationMixin):
            admin_class = type(
                f"Persian{admin_class.__name__}",
                (PersianAdminPresentationMixin, admin_class),
                {"__module__": admin_class.__module__},
            )
        return super().register(model_or_iterable, admin_class, **options)

    def get_app_list(self, request, app_label=None):
        return localize_app_list(super().get_app_list(request, app_label))
