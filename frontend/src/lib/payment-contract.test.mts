import assert from "node:assert/strict";
import test from "node:test";

import {
  isPaymentAttempt,
  parsePaymentAttempt,
  parseEmptyPaymentInput,
  parsePositiveId,
  parseVerificationInput,
} from "./payment-contract.ts";

const attempt = {
  id: 4,
  status: "PENDING",
  amount: "250000",
  currency: "IRR",
  payment_url: "https://pay.example/attempt",
  payment_identifier: null,
  created_at: "2026-10-10T10:00:00Z",
  updated_at: "2026-10-10T10:00:00Z",
};

test("accepts only the public payment-attempt contract", () => {
  assert.equal(isPaymentAttempt(attempt), true);
  assert.equal(isPaymentAttempt({ ...attempt, currency: "USD" }), false);
  assert.equal(isPaymentAttempt({ ...attempt, gateway_reference: "secret" }), true);
  assert.equal(isPaymentAttempt({ ...attempt, payment_identifier: "also-set" }), false);
  assert.equal("gateway_reference" in parsePaymentAttempt({ ...attempt, gateway_reference: "secret" })!, false);
});

test("validates payment route identifiers and empty initiation body", () => {
  assert.equal(parsePositiveId("14"), 14);
  assert.equal(parsePositiveId("0"), null);
  assert.deepEqual(parseEmptyPaymentInput({}), {});
  assert.equal(parseEmptyPaymentInput({ amount: "1" }), null);
});

test("bounds untrusted verification callback data", () => {
  assert.deepEqual(parseVerificationInput({ callbackData: { authority: "abc", status: "ok" } }), {
    callbackData: { authority: "abc", status: "ok" },
  });
  assert.equal(parseVerificationInput({ callbackData: [] }), null);
  assert.equal(parseVerificationInput({ callbackData: { value: "x".repeat(2_001) } }), null);
  assert.equal(parseVerificationInput({ callbackData: {}, orderId: 1 }), null);
});
