import assert from "node:assert/strict";
import test from "node:test";

import {
  isOwnProductReview,
  isProductReviewAggregate,
  isProductReviewPage,
  normalizeReviewSlug,
  parseReviewInput,
} from "./review-contract.ts";
import {
  aggregateAfterApprovedDeletion,
  REVIEW_STATUS_COPY,
} from "./review-presentation.ts";

const ownReview = {
  id: 1,
  rating: 4,
  comment: "کیفیت ساخت بسیار خوب است.",
  status: "PENDING",
  created_at: "2026-10-10T10:00:00Z",
  updated_at: "2026-10-10T10:00:00Z",
};

test("accepts only the exact rating and comment submission contract", () => {
  assert.deepEqual(parseReviewInput({ rating: 5, comment: "  عالی  " }), {
    rating: 5,
    comment: "عالی",
  });
  assert.equal(parseReviewInput({ rating: 0, comment: "متن" }), null);
  assert.equal(parseReviewInput({ rating: 1.5, comment: "متن" }), null);
  assert.equal(parseReviewInput({ rating: 5, comment: "   " }), null);
  assert.equal(
    parseReviewInput({ rating: 5, comment: "متن", status: "APPROVED" }),
    null,
  );
  assert.equal(
    parseReviewInput({ rating: 5, comment: "متن", customer: 2 }),
    null,
  );
});

test("validates own pending and rejected review states", () => {
  assert.equal(isOwnProductReview(ownReview), true);
  assert.equal(
    isOwnProductReview({ ...ownReview, status: "REJECTED" }),
    true,
  );
  assert.equal(isOwnProductReview({ ...ownReview, status: "EDITABLE" }), false);
  assert.match(REVIEW_STATUS_COPY.PENDING.message, /تأیید مدیر/);
  assert.match(REVIEW_STATUS_COPY.REJECTED.message, /حذف/);
});

test("validates approved public reviews without private identity fields", () => {
  const publicReview = {
    id: 1,
    rating: 5,
    comment: "زیبا",
    author_name: "مینا احمدی",
    created_at: "2026-10-10T10:00:00Z",
  };
  assert.equal(
    isProductReviewPage({
      count: 1,
      next: null,
      previous: null,
      results: [publicReview],
    }),
    true,
  );
  assert.equal(
    isProductReviewPage({
      count: 1,
      next: null,
      previous: null,
      results: [{ ...publicReview, email: "private@example.com" }],
    }),
    false,
  );
});

test("requires deterministic aggregate and empty-state representations", () => {
  assert.equal(
    isProductReviewAggregate({ average_rating: "4.5", review_count: 2 }),
    true,
  );
  assert.equal(
    isProductReviewAggregate({ average_rating: null, review_count: 0 }),
    true,
  );
  assert.equal(
    isProductReviewAggregate({ average_rating: "0.0", review_count: 0 }),
    false,
  );
});

test("updates the visible aggregate after deleting an approved own review", () => {
  assert.deepEqual(
    aggregateAfterApprovedDeletion(
      { average_rating: "4.0", review_count: 3 },
      2,
    ),
    { average_rating: "5.0", review_count: 2 },
  );
  assert.deepEqual(
    aggregateAfterApprovedDeletion(
      { average_rating: "5.0", review_count: 1 },
      5,
    ),
    { average_rating: null, review_count: 0 },
  );
});

test("normalizes only safe product slugs", () => {
  assert.equal(normalizeReviewSlug("میناکاری"), "میناکاری");
  assert.equal(normalizeReviewSlug("vase%2Fdelete"), null);
  assert.equal(normalizeReviewSlug(""), null);
});
