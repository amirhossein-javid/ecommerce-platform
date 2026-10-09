import assert from "node:assert/strict";
import test from "node:test";

import { classifyCheckoutFailure } from "./checkout-error-policy.ts";

test("maps authoritative checkout validation failures", () => {
  assert.equal(
    classifyCheckoutFailure(400, {
      detail: ["A usable shipping address is required."],
    }),
    "address-required",
  );
  assert.equal(
    classifyCheckoutFailure(400, {
      detail: ["An active, non-empty cart is required."],
    }),
    "cart-unavailable",
  );
  assert.equal(
    classifyCheckoutFailure(400, {
      detail: ["The cart contains an unavailable product."],
    }),
    "product-unavailable",
  );
  assert.equal(
    classifyCheckoutFailure(400, {
      detail: ["The cart quantity exceeds available stock."],
    }),
    "insufficient-stock",
  );
});

test("keeps auth, rate limits and uncertain transport outcomes distinct", () => {
  assert.equal(
    classifyCheckoutFailure(404, { detail: "Customer profile not found." }),
    "missing-profile",
  );
  assert.equal(classifyCheckoutFailure(429), "rate-limited");
  assert.equal(classifyCheckoutFailure(undefined, undefined, true), "outcome-unknown");
  assert.equal(classifyCheckoutFailure(503), "outcome-unknown");
  assert.equal(classifyCheckoutFailure(undefined), "upstream");
});
