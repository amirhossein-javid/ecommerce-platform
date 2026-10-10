import assert from "node:assert/strict";
import test from "node:test";

import {
  isManagedReviewPage,
  parseModerationInput,
  parseStoreReplyInput,
} from "./management-review-contract.ts";

const review = {
  id: 12,
  product: { id: 2, name: "گلدان میناکاری", slug: "mina-vase" },
  customer_display_name: "سارا اکبری",
  rating: 5,
  comment: "بسیار زیبا بود.",
  status: "PENDING",
  created_at: "2026-10-10T10:00:00Z",
  updated_at: "2026-10-10T10:00:00Z",
  store_reply: null,
};

test("validates managed review pages and optional replies", () => {
  assert.equal(
    isManagedReviewPage({ count: 1, next: null, previous: null, results: [review] }),
    true,
  );
  assert.equal(
    isManagedReviewPage({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          ...review,
          store_reply: {
            comment: "سپاس از شما.",
            created_at: "2026-10-10T11:00:00Z",
            updated_at: "2026-10-10T11:00:00Z",
          },
        },
      ],
    }),
    true,
  );
});

test("accepts only explicit moderation transitions", () => {
  assert.deepEqual(parseModerationInput({ status: "APPROVED" }), {
    status: "APPROVED",
  });
  assert.equal(parseModerationInput({ status: "PENDING" }), null);
  assert.equal(parseModerationInput({ status: "REJECTED", id: 1 }), null);
});

test("normalizes reply text and rejects extra or blank input", () => {
  assert.deepEqual(parseStoreReplyInput({ comment: "  سپاس  " }), {
    comment: "سپاس",
  });
  assert.equal(parseStoreReplyInput({ comment: "   " }), null);
  assert.equal(parseStoreReplyInput({ comment: "متن", review: 1 }), null);
});
