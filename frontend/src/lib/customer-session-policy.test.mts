import assert from "node:assert/strict";
import test from "node:test";

import { classifyCustomerProfileFailure } from "./customer-session-policy.ts";

test("existing missing-profile sessions never collapse to guest", () => {
  assert.equal(classifyCustomerProfileFailure(404), "missing-profile");
});

test("invalid authentication and upstream failures remain distinct", () => {
  assert.equal(classifyCustomerProfileFailure(401), "invalid");
  assert.equal(classifyCustomerProfileFailure(403), "invalid");
  assert.equal(classifyCustomerProfileFailure(500), "upstream-error");
  assert.equal(classifyCustomerProfileFailure(), "upstream-error");
});
