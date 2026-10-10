from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import DEFAULT_DB_ALIAS, connections, models, router, transaction
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils.text import slugify

from apps.common.money import validate_whole_rial

_CATEGORY_PARENT_LOCK_NAMESPACE = 1_127_329_857
_CATEGORY_PARENT_LOCK_KEY = 1


def lock_category_parent_structure(*, using):
    database = connections[using]
    if not database.in_atomic_block:
        raise RuntimeError("Category parent lock requires an active transaction.")
    with database.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            [_CATEGORY_PARENT_LOCK_NAMESPACE, _CATEGORY_PARENT_LOCK_KEY],
        )


class CategoryQuerySet(models.QuerySet):
    parent_fields = frozenset({"parent", "parent_id"})

    def update(self, **kwargs):
        if self.parent_fields.intersection(kwargs):
            raise TypeError("Category parent changes must use Category.save().")
        return super().update(**kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        if self.parent_fields.intersection(fields):
            raise TypeError("Category parent changes must use Category.save().")
        return super().bulk_update(objs, fields, batch_size=batch_size)

    def bulk_create(self, objs, *args, **kwargs):
        objs = list(objs)
        if any(category.parent_id is not None for category in objs):
            raise TypeError("Category parents cannot be assigned with bulk_create().")
        return super().bulk_create(objs, *args, **kwargs)


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

    objects = CategoryQuerySet.as_manager()

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
        if not parent_is_persisted:
            return super().save(*args, **kwargs)

        using = kwargs.get("using") or router.db_for_write(
            self.__class__,
            instance=self,
        )
        with transaction.atomic(using=using):
            lock_category_parent_structure(using=using)
            self._validate_parent_chain(using=using)
            return super().save(*args, **kwargs)

    def _set_slug_if_missing(self):
        if self.slug:
            return

        self.slug = slugify(self.name, allow_unicode=True)
        if not self.slug:
            raise ValidationError(
                {"slug": "A slug could not be generated from this name."}
            )

    def _validate_parent_chain(self, *, using=None):
        if self.parent_id is None:
            return

        using = using or self._state.db or DEFAULT_DB_ALIAS
        ancestor_id = self.parent_id
        visited_ids = {self.pk} if self.pk is not None else set()

        while ancestor_id is not None:
            if ancestor_id in visited_ids:
                raise ValidationError(
                    {"parent": "A category cannot be its own ancestor."}
                )
            visited_ids.add(ancestor_id)
            ancestor_id = (
                self.__class__.objects.using(using)
                .filter(pk=ancestor_id)
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
        validators=[MinValueValidator(Decimal("1.00")), validate_whole_rial],
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
                condition=Q(price=models.functions.Floor("price")),
                name="products_product_price_whole_irr",
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


class ProductReview(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="product_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5)),
    )
    comment = models.TextField(max_length=5000)
    status = models.CharField(
        max_length=8,
        choices=Status,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("product", "customer"),
                name="products_review_product_customer_unique",
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5),
                name="products_review_rating_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=Q(comment__regex=r"\S"),
                name="products_review_comment_not_blank",
            ),
        ]
        indexes = [
            models.Index(
                fields=("product", "status", "-created_at"),
                name="products_review_public_idx",
            )
        ]
        ordering = ("-created_at", "-pk")

    def __str__(self):
        return f"Review {self.pk} for {self.product}"


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

    def validate_constraints(self, exclude=None):
        exclusions = set(exclude or ())
        if self.is_primary:
            # Saving a primary image transactionally replaces the current primary.
            exclusions.add("is_primary")
        return super().validate_constraints(exclude=exclusions)

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
