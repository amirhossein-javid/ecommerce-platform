import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.models import CustomerProfile, User
from apps.products.admin import ProductReviewAdmin
from apps.products.models import Category, Product, ProductReview


@pytest.fixture
def review(db):
    category = Category.objects.create(name="Handicrafts")
    product = Product.objects.create(
        category=category,
        name="Vase",
        slug="vase",
        sku="VASE",
        price="1000",
    )
    customer = CustomerProfile.objects.create(
        user=User.objects.create_user("customer@example.com"),
        first_name="Sara",
        last_name="Akbari",
    )
    return ProductReview.objects.create(
        product=product,
        customer=customer,
        rating=5,
        comment="Beautiful craftsmanship with a detailed finish.",
    )


def create_operator(*, with_change_permission):
    operator = User.objects.create_user("operator@example.com", "strong-password")
    operator.is_staff = True
    operator.save(update_fields=("is_staff",))
    if with_change_permission:
        operator.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="products",
                codename="change_productreview",
            )
        )
    return operator


def run_action(client, action, review):
    return client.post(
        reverse("admin:products_productreview_changelist"),
        {
            "action": action,
            "_selected_action": [review.pk],
            "index": "0",
        },
    )


def test_product_review_uses_protected_admin():
    from django.contrib import admin

    assert isinstance(admin.site._registry[ProductReview], ProductReviewAdmin)


@pytest.mark.django_db
def test_staff_status_alone_does_not_authorize_moderation(client, review):
    operator = create_operator(with_change_permission=False)
    client.force_login(operator)

    response = run_action(client, "approve_reviews", review)
    detail_response = client.get(
        reverse("admin:products_productreview_change", args=(review.pk,))
    )

    assert response.status_code == 403
    assert detail_response.status_code == 403
    review.refresh_from_db()
    assert review.status == ProductReview.Status.PENDING


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("approve_reviews", ProductReview.Status.APPROVED),
        ("reject_reviews", ProductReview.Status.REJECTED),
    ],
)
def test_authorized_operator_can_moderate_pending_review(
    client,
    review,
    action,
    expected,
):
    operator = create_operator(with_change_permission=True)
    client.force_login(operator)

    response = run_action(client, action, review)

    assert response.status_code == 302
    review.refresh_from_db()
    assert review.status == expected


@pytest.mark.django_db
def test_authorized_operator_can_view_full_read_only_review_detail(client, review):
    operator = create_operator(with_change_permission=True)
    client.force_login(operator)

    response = client.get(
        reverse("admin:products_productreview_change", args=(review.pk,))
    )

    assert response.status_code == 200
    assert "Vase" in response.content.decode()
    assert "Sara Akbari" in response.content.decode()
    content = response.content.decode()
    assert review.comment in content
    assert review.get_status_display() in content
    assert "Created at" in content
    assert "Updated at" in content
    for field_name in ("product", "customer", "rating", "comment", "status"):
        assert f'name="{field_name}"'.encode() not in response.content
    assert b'name="_save"' not in response.content


@pytest.mark.django_db
def test_authorized_operator_changelist_links_to_review_detail(client, review):
    operator = create_operator(with_change_permission=True)
    client.force_login(operator)

    detail_url = reverse("admin:products_productreview_change", args=(review.pk,))
    response = client.get(reverse("admin:products_productreview_changelist"))

    assert response.status_code == 200
    assert f'href="{detail_url}"' in response.content.decode()


def test_review_detail_fields_are_explicitly_read_only():
    from django.contrib import admin

    review_admin = admin.site._registry[ProductReview]

    assert review_admin.fields == (
        "product",
        "customer_display_name",
        "rating",
        "comment",
        "status",
        "created_at",
        "updated_at",
    )
    assert review_admin.readonly_fields == review_admin.fields


@pytest.mark.django_db
def test_admin_does_not_remoderate_or_directly_edit_review(client, review):
    operator = create_operator(with_change_permission=True)
    review.status = ProductReview.Status.APPROVED
    review.save(update_fields=("status",))
    client.force_login(operator)

    action_response = run_action(client, "reject_reviews", review)
    change_response = client.post(
        reverse("admin:products_productreview_change", args=(review.pk,)),
        {"status": ProductReview.Status.REJECTED, "_save": "Save"},
    )

    assert action_response.status_code == 302
    assert change_response.status_code == 403
    review.refresh_from_db()
    assert review.status == ProductReview.Status.APPROVED
