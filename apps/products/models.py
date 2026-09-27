from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        allow_unicode=True,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(parent__isnull=True) | ~Q(parent=F("id")),
                name="products_category_not_own_parent",
            )
        ]

    def clean(self):
        super().clean()
        self._set_slug_if_missing()
        self._validate_parent_chain()

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        persisted_fields = set(update_fields) if update_fields is not None else None

        slug_is_persisted = (
            self._state.adding or persisted_fields is None or "slug" in persisted_fields
        )
        if slug_is_persisted:
            self._set_slug_if_missing()
            try:
                self._meta.get_field("slug").run_validators(self.slug)
            except ValidationError as error:
                raise ValidationError({"slug": error.error_list}) from error

        parent_is_persisted = (
            self._state.adding
            or persisted_fields is None
            or bool({"parent", "parent_id"} & persisted_fields)
        )
        if parent_is_persisted:
            self._validate_parent_chain()

        return super().save(*args, **kwargs)

    def _set_slug_if_missing(self):
        if self.slug:
            return

        self.slug = slugify(self.name, allow_unicode=True)
        if not self.slug:
            raise ValidationError(
                {"slug": "A slug could not be generated from this name."}
            )

    def _validate_parent_chain(self):
        if self.parent_id is None:
            return

        ancestor_id = self.parent_id
        visited_ids = {self.pk} if self.pk is not None else set()

        while ancestor_id is not None:
            if ancestor_id in visited_ids:
                raise ValidationError(
                    {"parent": "A category cannot be its own ancestor."}
                )
            visited_ids.add(ancestor_id)
            ancestor_id = (
                self.__class__.objects.filter(pk=ancestor_id)
                .values_list("parent_id", flat=True)
                .first()
            )

    def __str__(self):
        return self.name
