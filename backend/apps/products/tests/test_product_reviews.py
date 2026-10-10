from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import connections
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
def active_product(db):
    category = Category.objects.create(name="Handicrafts")
    return Product.objects.create(
        category=category,
        name="Enamel Vase",
        slug="enamel-vase",
        sku="ENAMEL-VASE",
        price="100000",
        stock_quantity=1,
        status=Product.Status.ACTIVE,
    )


@pytest.fixture
def customer(db):
    user = User.objects.create_user("customer@example.com", "strong-password")
    profile = CustomerProfile.objects.create(
        user=user,
        first_name="Ali",
        last_name="Ahmadi",
    )
    return user, profile


def authenticate(client, user):
    access_token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")


def own_review_url(product):
    return reverse("products:own-product-review", kwargs={"slug": product.slug})


def create_review(product, profile, **overrides):
    return ProductReview.objects.create(
        product=product,
        customer=profile,
        rating=overrides.pop("rating", 5),
        comment=overrides.pop("comment", "Excellent craftsmanship."),
        **overrides,
    )


@pytest.mark.django_db
def test_anonymous_customer_cannot_submit_review(api_client, active_product):
    response = api_client.post(
        own_review_url(active_product),
        {"rating": 5, "comment": "Beautiful"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert ProductReview.objects.exists() is False


@pytest.mark.django_db
def test_customer_can_submit_without_purchase_and_server_derives_private_fields(
    api_client,
    active_product,
    customer,
):
    user, profile = customer
    other_user = User.objects.create_user("other@example.com", "strong-password")
    other_profile = CustomerProfile.objects.create(user=other_user)
    authenticate(api_client, user)

    response = api_client.post(
        own_review_url(active_product),
        {
            "rating": 4,
            "comment": "  Lovely details.  ",
            "customer": other_profile.pk,
            "status": ProductReview.Status.APPROVED,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert set(response.json()) == {"customer", "status"}
    assert ProductReview.objects.exists() is False

    response = api_client.post(
        own_review_url(active_product),
        {"rating": 4, "comment": "  Lovely details.  "},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    review = ProductReview.objects.get()
    assert review.customer == profile
    assert review.product == active_product
    assert review.status == ProductReview.Status.PENDING
    assert review.comment == "Lovely details."


@pytest.mark.django_db
@pytest.mark.parametrize("rating", [0, 6, 1.5, "excellent", None])
def test_review_rating_validation(api_client, active_product, customer, rating):
    authenticate(api_client, customer[0])

    response = api_client.post(
        own_review_url(active_product),
        {"rating": rating, "comment": "Comment"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "rating" in response.json()


@pytest.mark.django_db
@pytest.mark.parametrize("comment", ["", "   ", "\n\t"])
def test_review_comment_must_contain_text(
    api_client,
    active_product,
    customer,
    comment,
):
    authenticate(api_client, customer[0])

    response = api_client.post(
        own_review_url(active_product),
        {"rating": 5, "comment": comment},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "comment" in response.json()


@pytest.mark.django_db
def test_authenticated_user_without_profile_fails_safely(api_client, active_product):
    user = User.objects.create_user("profileless@example.com", "strong-password")
    authenticate(api_client, user)

    response = api_client.post(
        own_review_url(active_product),
        {"rating": 5, "comment": "Comment"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Customer profile not found."}


@pytest.mark.django_db
def test_duplicate_review_returns_conflict(api_client, active_product, customer):
    user, profile = customer
    create_review(active_product, profile)
    authenticate(api_client, user)

    response = api_client.post(
        own_review_url(active_product),
        {"rating": 3, "comment": "Another"},
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert ProductReview.objects.filter(product=active_product).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_submission_creates_exactly_one_review(active_product):
    user = User.objects.create_user("concurrent@example.com", "strong-password")
    CustomerProfile.objects.create(user=user)
    tokens = [
        str(RefreshToken.for_user(user).access_token),
        str(RefreshToken.for_user(user).access_token),
    ]
    barrier = Barrier(2)

    def submit(access_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        barrier.wait()
        try:
            return client.post(
                own_review_url(active_product),
                {"rating": 5, "comment": "Concurrent"},
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
    assert ProductReview.objects.filter(product=active_product).count() == 1


@pytest.mark.django_db
def test_public_list_and_aggregate_include_only_approved_reviews(
    api_client,
    active_product,
    customer,
):
    _, approved_profile = customer
    pending_user = User.objects.create_user("pending@example.com")
    pending_profile = CustomerProfile.objects.create(user=pending_user)
    rejected_user = User.objects.create_user("rejected@example.com")
    rejected_profile = CustomerProfile.objects.create(user=rejected_user)
    approved_review = create_review(
        active_product,
        approved_profile,
        rating=4,
        status=ProductReview.Status.APPROVED,
    )
    ProductReviewReply.objects.create(
        review=approved_review,
        comment="سپاس از همراهی شما.",
    )
    create_review(
        active_product,
        pending_profile,
        rating=1,
        status=ProductReview.Status.PENDING,
    )
    create_review(
        active_product,
        rejected_profile,
        rating=2,
        status=ProductReview.Status.REJECTED,
    )

    list_response = api_client.get(
        reverse("products:product-review-list", kwargs={"slug": active_product.slug})
    )
    aggregate_response = api_client.get(
        reverse(
            "products:product-review-aggregate",
            kwargs={"slug": active_product.slug},
        )
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.json()["count"] == 1
    public_review = list_response.json()["results"][0]
    assert public_review["rating"] == 4
    assert public_review["author_name"] == "Ali Ahmadi"
    assert public_review["store_reply"]["comment"] == "سپاس از همراهی شما."
    assert "email" not in public_review
    assert "status" not in public_review
    assert aggregate_response.json() == {
        "average_rating": "4.0",
        "review_count": 1,
    }


@pytest.mark.django_db
def test_empty_aggregate_is_explicit(api_client, active_product):
    response = api_client.get(
        reverse(
            "products:product-review-aggregate",
            kwargs={"slug": active_product.slug},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"average_rating": None, "review_count": 0}


@pytest.mark.django_db
def test_own_review_is_isolated_and_exposes_moderation_status(
    api_client,
    active_product,
    customer,
):
    user, profile = customer
    own_review = create_review(
        active_product,
        profile,
        status=ProductReview.Status.REJECTED,
    )
    other_user = User.objects.create_user("other@example.com")
    CustomerProfile.objects.create(user=other_user)
    authenticate(api_client, other_user)

    missing_response = api_client.get(own_review_url(active_product))
    assert missing_response.status_code == status.HTTP_404_NOT_FOUND

    authenticate(api_client, user)
    response = api_client.get(own_review_url(active_product))
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == own_review.pk
    assert response.json()["status"] == ProductReview.Status.REJECTED


@pytest.mark.django_db
def test_customer_cannot_edit_review(api_client, active_product, customer):
    user, profile = customer
    review = create_review(active_product, profile)
    authenticate(api_client, user)

    for method in (api_client.patch, api_client.put):
        response = method(
            own_review_url(active_product),
            {"rating": 1, "comment": "Changed"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    review.refresh_from_db()
    assert review.rating == 5
    assert review.comment == "Excellent craftsmanship."


@pytest.mark.django_db
def test_customer_can_delete_and_resubmit(api_client, active_product, customer):
    user, profile = customer
    original = create_review(
        active_product,
        profile,
        status=ProductReview.Status.APPROVED,
    )
    authenticate(api_client, user)

    delete_response = api_client.delete(own_review_url(active_product))
    create_response = api_client.post(
        own_review_url(active_product),
        {"rating": 2, "comment": "Replacement"},
        format="json",
    )

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert ProductReview.objects.filter(pk=original.pk).exists() is False
    assert create_response.status_code == status.HTTP_201_CREATED
    replacement = ProductReview.objects.get()
    assert replacement.status == ProductReview.Status.PENDING
    assert replacement.rating == 2


@pytest.mark.django_db
def test_unknown_or_unavailable_products_are_hidden(
    api_client,
    active_product,
    customer,
):
    active_product.status = Product.Status.DRAFT
    active_product.save(update_fields=("status",))
    authenticate(api_client, customer[0])

    for name in (
        "product-review-list",
        "product-review-aggregate",
        "own-product-review",
    ):
        response = api_client.get(
            reverse(f"products:{name}", kwargs={"slug": active_product.slug})
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_review_mutations_are_throttled(
    api_client,
    active_product,
    customer,
    configure_throttle_rates,
):
    configure_throttle_rates(review_mutation="1/hour")
    authenticate(api_client, customer[0])

    first = api_client.post(
        own_review_url(active_product),
        {"rating": 5, "comment": "First"},
        format="json",
    )
    second = api_client.delete(own_review_url(active_product))

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second.has_header("Retry-After")


@pytest.mark.django_db
def test_review_openapi_exposes_no_customer_update_operation(api_client):
    response = api_client.get(reverse("schema"), HTTP_ACCEPT="application/json")

    assert response.status_code == status.HTTP_200_OK
    path = response.json()["paths"]["/api/v1/products/{slug}/reviews/mine/"]
    assert {
        method for method in path if method in {"get", "post", "put", "patch", "delete"}
    } == {
        "get",
        "post",
        "delete",
    }
