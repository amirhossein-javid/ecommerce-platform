from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q
from django.db.models.functions import Lower
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


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        allow_unicode=True,
    )
    sku = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=8,
        choices=Status,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("sku"),
                name="products_product_sku_ci_unique",
            ),
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name="products_product_price_gt_zero",
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="products_product_stock_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        self._set_slug_if_missing()

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

        return super().save(*args, **kwargs)

    def _set_slug_if_missing(self):
        if self.slug:
            return

        self.slug = slugify(self.name, allow_unicode=True)
        if not self.slug:
            raise ValidationError(
                {"slug": "A slug could not be generated from this name."}
            )

    def __str__(self):
        return self.name


def product_image_upload_to(instance, filename):
    return f"products/{instance.product_id}/{filename}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=product_image_upload_to)
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    position = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("product",),
                condition=Q(is_primary=True),
                name="products_unique_primary_image_per_product",
            ),
            models.UniqueConstraint(
                fields=("product", "position"),
                name="products_unique_image_position_per_product",
            ),
            models.CheckConstraint(
                condition=Q(position__gte=0),
                name="products_product_image_position_nonnegative",
            ),
        ]

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        persisted_fields = set(update_fields) if update_fields is not None else None
        primary_is_persisted = (
            self._state.adding
            or persisted_fields is None
            or "is_primary" in persisted_fields
        )

        if not primary_is_persisted or self.product_id is None:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            Product.objects.select_for_update().get(pk=self.product_id)
            product_images = self.__class__.objects.filter(product_id=self.product_id)

            if self._state.adding and not product_images.exists():
                self.is_primary = True

            if self.is_primary:
                product_images.filter(is_primary=True).exclude(pk=self.pk).update(
                    is_primary=False
                )

            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk is None or self.product_id is None:
            return super().delete(*args, **kwargs)

        product_id = self.product_id
        with transaction.atomic():
            Product.objects.select_for_update().get(pk=product_id)
            current = (
                self.__class__.objects.filter(pk=self.pk).values("is_primary").first()
            )
            was_primary = current is not None and current["is_primary"]

            result = super().delete(*args, **kwargs)

            if was_primary:
                replacement = (
                    self.__class__.objects.filter(product_id=product_id)
                    .order_by("position", "pk")
                    .first()
                )
                if replacement is not None:
                    self.__class__.objects.filter(pk=replacement.pk).update(
                        is_primary=True
                    )

            return result

    def __str__(self):
        return f"Image for {self.product} at position {self.position}"
