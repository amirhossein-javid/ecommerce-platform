import { isValidProductSlug } from "./cart-contract.ts";

export const MAX_REVIEW_COMMENT_LENGTH = 5000;

export type ReviewStatus = "PENDING" | "APPROVED" | "REJECTED";

export type PublicProductReview = {
  id: number;
  rating: number;
  comment: string;
  author_name: string;
  created_at: string;
  store_reply: {
    comment: string;
    created_at: string;
    updated_at: string;
  } | null;
};

export type OwnProductReview = {
  id: number;
  rating: number;
  comment: string;
  status: ReviewStatus;
  created_at: string;
  updated_at: string;
};

export type ProductReviewAggregate = {
  average_rating: string | null;
  review_count: number;
};

export type ProductReviewPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: PublicProductReview[];
};

export type ReviewInput = {
  rating: number;
  comment: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}

function isRating(value: unknown): value is number {
  return Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 5;
}

function isIsoDate(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function hasExactKeys(value: Record<string, unknown>, expected: string[]) {
  const keys = Object.keys(value);
  return keys.length === expected.length && expected.every((key) => key in value);
}

export function parseReviewInput(value: unknown): ReviewInput | null {
  if (!isRecord(value) || !hasExactKeys(value, ["rating", "comment"])) {
    return null;
  }
  if (!isRating(value.rating) || typeof value.comment !== "string") {
    return null;
  }
  const comment = value.comment.trim();
  if (!comment || comment.length > MAX_REVIEW_COMMENT_LENGTH) {
    return null;
  }
  return { rating: value.rating, comment };
}

export function normalizeReviewSlug(value: string) {
  try {
    const slug = decodeURIComponent(value).trim();
    return isValidProductSlug(slug) ? slug : null;
  } catch {
    return null;
  }
}

export function isPublicProductReview(value: unknown): value is PublicProductReview {
  if (!isRecord(value)) return false;
  const reply = value.store_reply;
  const validReply =
    reply === null ||
    (isRecord(reply) &&
      typeof reply.comment === "string" &&
      reply.comment.trim().length > 0 &&
      isIsoDate(reply.created_at) &&
      isIsoDate(reply.updated_at));
  return (
    hasExactKeys(value, [
      "id",
      "rating",
      "comment",
      "author_name",
      "created_at",
      "store_reply",
    ]) &&
    isPositiveInteger(value.id) &&
    isRating(value.rating) &&
    typeof value.comment === "string" &&
    value.comment.trim().length > 0 &&
    typeof value.author_name === "string" &&
    value.author_name.trim().length > 0 &&
    isIsoDate(value.created_at) &&
    validReply
  );
}

export function isOwnProductReview(value: unknown): value is OwnProductReview {
  if (!isRecord(value)) return false;
  return (
    hasExactKeys(value, [
      "id",
      "rating",
      "comment",
      "status",
      "created_at",
      "updated_at",
    ]) &&
    isPositiveInteger(value.id) &&
    isRating(value.rating) &&
    typeof value.comment === "string" &&
    value.comment.trim().length > 0 &&
    (value.status === "PENDING" ||
      value.status === "APPROVED" ||
      value.status === "REJECTED") &&
    isIsoDate(value.created_at) &&
    isIsoDate(value.updated_at)
  );
}

export function isProductReviewPage(value: unknown): value is ProductReviewPage {
  if (!isRecord(value)) return false;
  return (
    hasExactKeys(value, ["count", "next", "previous", "results"]) &&
    Number.isSafeInteger(value.count) &&
    Number(value.count) >= 0 &&
    (value.next === null || typeof value.next === "string") &&
    (value.previous === null || typeof value.previous === "string") &&
    Array.isArray(value.results) &&
    value.results.every(isPublicProductReview)
  );
}

export function isProductReviewAggregate(
  value: unknown,
): value is ProductReviewAggregate {
  if (!isRecord(value)) return false;
  const validAverage =
    value.average_rating === null ||
    (typeof value.average_rating === "string" &&
      /^(?:[1-4]\.\d|5\.0)$/.test(value.average_rating));
  return (
    hasExactKeys(value, ["average_rating", "review_count"]) &&
    validAverage &&
    Number.isSafeInteger(value.review_count) &&
    Number(value.review_count) >= 0 &&
    (value.review_count === 0) === (value.average_rating === null)
  );
}
