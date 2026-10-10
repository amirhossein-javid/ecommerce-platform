export const MAX_STORE_REPLY_LENGTH = 5000;

export type ManagedReviewStatus = "PENDING" | "APPROVED" | "REJECTED";

export type StoreReply = {
  comment: string;
  created_at: string;
  updated_at: string;
};

export type ManagedReview = {
  id: number;
  product: { id: number; name: string; slug: string };
  customer_display_name: string;
  rating: number;
  comment: string;
  status: ManagedReviewStatus;
  created_at: string;
  updated_at: string;
  store_reply: StoreReply | null;
};

export type ManagedReviewPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ManagedReview[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}

function isIsoDate(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function isStatus(value: unknown): value is ManagedReviewStatus {
  return value === "PENDING" || value === "APPROVED" || value === "REJECTED";
}

export function isStoreReply(value: unknown): value is StoreReply {
  return (
    isRecord(value) &&
    typeof value.comment === "string" &&
    value.comment.trim().length > 0 &&
    isIsoDate(value.created_at) &&
    isIsoDate(value.updated_at)
  );
}

export function isManagedReview(value: unknown): value is ManagedReview {
  if (!isRecord(value) || !isRecord(value.product)) return false;
  return (
    isPositiveInteger(value.id) &&
    isPositiveInteger(value.product.id) &&
    typeof value.product.name === "string" &&
    typeof value.product.slug === "string" &&
    typeof value.customer_display_name === "string" &&
    Number.isInteger(value.rating) &&
    Number(value.rating) >= 1 &&
    Number(value.rating) <= 5 &&
    typeof value.comment === "string" &&
    isStatus(value.status) &&
    isIsoDate(value.created_at) &&
    isIsoDate(value.updated_at) &&
    (value.store_reply === null || isStoreReply(value.store_reply))
  );
}

export function isManagedReviewPage(value: unknown): value is ManagedReviewPage {
  return (
    isRecord(value) &&
    Number.isSafeInteger(value.count) &&
    Number(value.count) >= 0 &&
    (value.next === null || typeof value.next === "string") &&
    (value.previous === null || typeof value.previous === "string") &&
    Array.isArray(value.results) &&
    value.results.every(isManagedReview)
  );
}

export function parseStoreReplyInput(value: unknown) {
  if (!isRecord(value) || Object.keys(value).length !== 1) return null;
  if (typeof value.comment !== "string") return null;
  const comment = value.comment.trim();
  if (!comment || comment.length > MAX_STORE_REPLY_LENGTH) return null;
  return { comment };
}

export function parseModerationInput(
  value: unknown,
): { status: "APPROVED" | "REJECTED" } | null {
  if (!isRecord(value) || Object.keys(value).length !== 1) return null;
  const status = value.status;
  return status === "APPROVED" || status === "REJECTED" ? { status } : null;
}
