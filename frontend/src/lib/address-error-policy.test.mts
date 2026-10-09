import assert from "node:assert/strict";
import test from "node:test";

import { classifyAddressApiFailure } from "./address-error-policy.ts";

test("distinguishes a missing customer profile from ownership-hiding 404", () => {
  assert.equal(
    classifyAddressApiFailure(404, { detail: "Customer profile not found." }),
    "missing-profile",
  );
  assert.equal(
    classifyAddressApiFailure(404, { detail: "Address not found." }),
    "not-found",
  );
});

test("preserves validation, throttling and upstream failure classes", () => {
  assert.equal(classifyAddressApiFailure(400, { city: ["Required."] }), "validation");
  assert.equal(classifyAddressApiFailure(429), "rate-limited");
  assert.equal(classifyAddressApiFailure(503), "upstream");
  assert.equal(classifyAddressApiFailure(), "upstream");
});
