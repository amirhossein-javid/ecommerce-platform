from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.contrib.auth.models import Permission
from django.db import IntegrityError, connections, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomerProfile, User
from apps.products.models import Category, Product, ProductReview, ProductReviewReply


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def review(db):
    category = Category.objects.create(name="Handicrafts")
    product = Product.objects.create(
        category=category,
        name="Painted vase",
        slug="painted-vase",
        sku="PAINTED-VASE",
        price="12000",
        status=Product.Status.ACTIVE,
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
        comment="Beautiful craftsmanship.",
    )


def create_operator(*permissions):
    operator = User.objects.create_user("operator@example.com", "password")
    operator.is_staff = True
    operator.save(update_fields=("is_staff",))
    if permissions:
        operator.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="products",
                codename__in=permissions,
            )
        )
    return operator


def authenticate(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.mark.django_db
def test_staff_status_alone_cannot_access_review_management(api_client, review):
    authenticate(api_client, create_operator())

    list_response = api_client.get(reverse("products:review-management-list"))
    moderation_response = api_client.post(
        reverse("products:review-management-moderate", args=(review.pk,)),
        {"status": ProductReview.Status.APPROVED},
        format="json",
    )
    reply_response = api_client.post(
        reverse("products:review-management-reply", args=(review.pk,)),
        {"comment": "Thank you."},
        format="json",
    )

    assert list_response.status_code == status.HTTP_403_FORBIDDEN
    assert moderation_response.status_code == status.HTTP_403_FORBIDDEN
    assert reply_response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_authorized_operator_can_list_filter_and_view_reviews(api_client, review):
    authenticate(api_client, create_operator("view_productreview"))

    response = api_client.get(
        reverse("products:review-management-list"),
        {"status": ProductReview.Status.PENDING, "search": "Sara"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["count"] == 1
    managed_review = response.json()["results"][0]
    assert managed_review["id"] == review.pk
    assert managed_review["product"]["name"] == "Painted vase"
    assert managed_review["customer_display_name"] == "Sara Akbari"
    assert managed_review["comment"] == "Beautiful craftsmanship."
    assert managed_review["store_reply"] is None


@pytest.mark.django_db
def test_moderation_requires_change_permission_and_only_changes_pending(
    api_client,
    review,
):
    authenticate(api_client, create_operator("change_productreview"))
    url = reverse("products:review-management-moderate", args=(review.pk,))

    response = api_client.post(
        url,
        {"status": ProductReview.Status.APPROVED},
        format="json",
    )
    replay = api_client.post(
        url,
        {"status": ProductReview.Status.REJECTED},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == ProductReview.Status.APPROVED
    assert replay.status_code == status.HTTP_409_CONFLICT
    review.refresh_from_db()
    assert review.status == ProductReview.Status.APPROVED


@pytest.mark.django_db
def test_reply_crud_uses_explicit_model_permissions(api_client, review):
    operator = create_operator(
        "view_productreview",
        "add_productreviewreply",
        "change_productreviewreply",
        "delete_productreviewreply",
    )
    authenticate(api_client, operator)
    url = reverse("products:review-management-reply", args=(review.pk,))

    created = api_client.post(url, {"comment": "  سپاس از نظر شما.  "}, format="json")
    updated = api_client.patch(url, {"comment": "پاسخ ویرایش‌شده"}, format="json")
    deleted = api_client.delete(url)

    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["comment"] == "سپاس از نظر شما."
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["comment"] == "پاسخ ویرایش‌شده"
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert ProductReviewReply.objects.filter(review=review).exists() is False


@pytest.mark.django_db
def test_reply_permissions_are_not_interchangeable(api_client, review):
    authenticate(
        api_client,
        create_operator("view_productreview", "add_productreviewreply"),
    )
    url = reverse("products:review-management-reply", args=(review.pk,))

    created = api_client.post(url, {"comment": "Thank you."}, format="json")
    updated = api_client.patch(url, {"comment": "Changed"}, format="json")
    deleted = api_client.delete(url)

    assert created.status_code == status.HTTP_201_CREATED
    assert updated.status_code == status.HTTP_403_FORBIDDEN
    assert deleted.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_reply_is_one_to_one_at_database_level(review):
    ProductReviewReply.objects.create(review=review, comment="First reply")

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductReviewReply.objects.create(review=review, comment="Second reply")


@pytest.mark.django_db(transaction=True)
def test_concurrent_reply_creation_creates_exactly_one_reply(review):
    operator = create_operator(
        "view_productreview",
        "add_productreviewreply",
    )
    tokens = [
        str(RefreshToken.for_user(operator).access_token),
        str(RefreshToken.for_user(operator).access_token),
    ]
    barrier = Barrier(2)
    url = reverse("products:review-management-reply", args=(review.pk,))

    def submit(access_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        barrier.wait()
        try:
            return client.post(
                url,
                {"comment": "Concurrent reply"},
                format="json",
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        response_statuses = list(executor.map(submit, tokens))

    assert sorted(response_statuses) == [
        status.HTTP_201_CREATED,
        status.HTTP_409_CONFLICT,
    ]
    assert ProductReviewReply.objects.filter(review=review).count() == 1


@pytest.mark.django_db
def test_public_api_never_exposes_reply_for_unapproved_review(api_client, review):
    ProductReviewReply.objects.create(review=review, comment="Hidden reply")

    response = api_client.get(
        reverse(
            "products:product-review-list",
            kwargs={"slug": review.product.slug},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"] == []
