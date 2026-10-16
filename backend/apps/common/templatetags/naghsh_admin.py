from django import template
from django.core.exceptions import FieldDoesNotExist
from django.db import models

from apps.common.admin_presentation import (
    APP_LABELS,
    admin_model_label,
    format_admin_temporal,
    translate_admin_text,
)

register = template.Library()


@register.simple_tag
def admin_app_label(opts):
    if not hasattr(opts, "app_label"):
        model = getattr(opts, "model", None)
        opts = getattr(model, "_meta", opts)
    return APP_LABELS.get(opts.app_label, opts.app_config.verbose_name)


@register.simple_tag
def admin_model_name(opts, plural=False):
    return admin_model_label(opts, plural=plural)


@register.filter
def admin_fa(value):
    return translate_admin_text(value)


@register.simple_tag
def admin_field_label(field):
    if field.is_readonly:
        label = translate_admin_text(field.field["label"])
        field.field["label"] = label
        return field.label_tag()
    label = translate_admin_text(field.field.label)
    return field.field.label_tag(label)


@register.simple_tag
def admin_readonly_contents(field):
    field_name = field.field["field"]
    if isinstance(field_name, str):
        try:
            model_field = field.form._meta.model._meta.get_field(field_name)
        except FieldDoesNotExist:
            pass
        else:
            if isinstance(model_field, (models.DateField, models.DateTimeField)):
                return format_admin_temporal(
                    getattr(field.form.instance, field_name, None)
                )
            if model_field.choices:
                display = getattr(
                    field.form.instance,
                    f"get_{field_name}_display",
                )()
                return translate_admin_text(display)
    return field.contents()
