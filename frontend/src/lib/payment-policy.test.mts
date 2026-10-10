import assert from "node:assert/strict";
import test from "node:test";

import { canRetryPayment, classifyPaymentFailure } from "./payment-policy.ts";

test("classifies ownership, expiry, throttling and gateway failures", () => {
  assert.equal(classifyPaymentFailure(404, { detail: "Order not found." }), "not-found");
  assert.equal(classifyPaymentFailure(404, { detail: "Customer profile not found." }), "missing-profile");
  assert.equal(classifyPaymentFailure(409, { detail: "The order payment window has expired." }), "expired");
  assert.equal(classifyPaymentFailure(409, { detail: "The order is not pending payment." }), "not-payable");
  assert.equal(classifyPaymentFailure(429), "rate-limited");
  assert.equal(classifyPaymentFailure(502), "gateway-invalid");
  assert.equal(classifyPaymentFailure(503), "gateway-unavailable");
});

test("allows retry only while Django still considers the order unpaid", () => {
  assert.equal(canRetryPayment("PENDING_PAYMENT"), true);
  assert.equal(canRetryPayment("PENDING_PAYMENT", "FAILED"), true);
  assert.equal(canRetryPayment("PENDING_PAYMENT", "SUCCESS"), false);
  assert.equal(canRetryPayment("PAID", "FAILED"), false);
  assert.equal(canRetryPayment("EXPIRED"), false);
});
