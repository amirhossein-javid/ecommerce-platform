import assert from "node:assert/strict";
import test from "node:test";

import {
  classifyCartMergeFailure,
  successfulCartMerge,
} from "./cart-merge-policy.ts";

test("successful merge consumes the guest identity and establishes the session", () => {
  assert.deepEqual(successfulCartMerge(), {
    state: "merged",
    clearGuestCookie: true,
    establishSession: true,
  });
});

test("consumed or stale credentials are cleared without claiming merge success", () => {
  assert.deepEqual(classifyCartMergeFailure(404), {
    state: "unavailable",
    clearGuestCookie: true,
    establishSession: true,
  });
});

test("temporary failures preserve the guest identity for an explicit retry", () => {
  for (const status of [400, 429, 500, 503, undefined]) {
    assert.deepEqual(classifyCartMergeFailure(status), {
      state: "pending",
      clearGuestCookie: false,
      establishSession: true,
    });
  }
});

test("authentication failure preserves the guest cart and rejects the session", () => {
  for (const status of [401, 403]) {
    assert.deepEqual(classifyCartMergeFailure(status), {
      state: "authentication-failure",
      clearGuestCookie: false,
      establishSession: false,
    });
  }
});
