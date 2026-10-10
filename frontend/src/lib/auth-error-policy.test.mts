import assert from "node:assert/strict";
import test from "node:test";

import { isAuthenticationFailure } from "./auth-error-policy.ts";

test("recognizes authentication failures across account and cart API errors", () => {
  assert.equal(isAuthenticationFailure({ status: 401 }), true);
  assert.equal(isAuthenticationFailure({ status: 403 }), true);
  assert.equal(isAuthenticationFailure({ status: 404 }), false);
  assert.equal(isAuthenticationFailure(new Error("network")), false);
});
