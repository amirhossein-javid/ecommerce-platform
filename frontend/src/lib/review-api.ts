import "server-only";

import {
  isOwnProductReview,
  isProductReviewAggregate,
  isProductReviewPage,
  type OwnProductReview,
  type ProductReviewAggregate,
  type ProductReviewPage,
  type ReviewInput,
} from "@/lib/review-contract";

const PRODUCTS_PATH = "/api/v1/products/";

export class ReviewApiError extends Error {
  constructor(
    public readonly status?: number,
    public readonly payload?: unknown,
    public readonly retryAfter?: string | null,
  ) {
    super("The product review API request failed.");
    this.name = "ReviewApiError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;
  if (!value) throw new ReviewApiError();
  try {
    return new URL(value);
  } catch {
    throw new ReviewApiError();
  }
}

async function parsePayload(response: Response) {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

async function requestReview(path: string, init: RequestInit) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  let response: Response;
  try {
    response = await fetch(new URL(path, getApiOrigin()), {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ReviewApiError();
  }
  if (!response.ok) {
    throw new ReviewApiError(
      response.status,
      await parsePayload(response),
      response.headers.get("retry-after"),
    );
  }
  return response;
}

function reviewPath(slug: string, suffix = "") {
  return `${PRODUCTS_PATH}${encodeURIComponent(slug)}/reviews/${suffix}`;
}

export async function fetchPublicProductReviews(
  slug: string,
): Promise<ProductReviewPage> {
  const response = await requestReview(reviewPath(slug), { method: "GET" });
  const payload = await parsePayload(response);
  if (!isProductReviewPage(payload)) throw new ReviewApiError();
  return payload;
}

export async function fetchProductReviewAggregate(
  slug: string,
): Promise<ProductReviewAggregate> {
  const response = await requestReview(reviewPath(slug, "aggregate/"), {
    method: "GET",
  });
  const payload = await parsePayload(response);
  if (!isProductReviewAggregate(payload)) throw new ReviewApiError();
  return payload;
}

export async function fetchOwnProductReview(
  access: string,
  slug: string,
): Promise<OwnProductReview> {
  const response = await requestReview(reviewPath(slug, "mine/"), {
    method: "GET",
    headers: { Authorization: `Bearer ${access}` },
  });
  const payload = await parsePayload(response);
  if (!isOwnProductReview(payload)) throw new ReviewApiError();
  return payload;
}

export async function createOwnProductReview(
  access: string,
  slug: string,
  input: ReviewInput,
): Promise<OwnProductReview> {
  const response = await requestReview(reviewPath(slug, "mine/"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${access}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  const payload = await parsePayload(response);
  if (!isOwnProductReview(payload)) throw new ReviewApiError();
  return payload;
}

export async function deleteOwnProductReview(access: string, slug: string) {
  await requestReview(reviewPath(slug, "mine/"), {
    method: "DELETE",
    headers: { Authorization: `Bearer ${access}` },
  });
}
