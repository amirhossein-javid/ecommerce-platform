import assert from "node:assert/strict";
import test from "node:test";

import { validatePaymentRedirect } from "./payment-redirect-policy.ts";

test("accepts only exact configured HTTPS payment origins", () => {
  const allowed = "https://pay.example,https://wallet.example";
  assert.equal(
    validatePaymentRedirect("https://pay.example/session?id=1", allowed),
    "https://pay.example/session?id=1",
  );
  assert.equal(validatePaymentRedirect("https://evil.example/session", allowed), null);
  assert.equal(validatePaymentRedirect("http://pay.example/session", allowed), null);
  assert.equal(validatePaymentRedirect("https://pay.example.evil.test/session", allowed), null);
  assert.equal(validatePaymentRedirect("https://user@pay.example/session", allowed), null);
});

test("allows an explicitly configured loopback simulator in development", () => {
  assert.equal(
    validatePaymentRedirect("http://localhost:9000/pay/1", "http://localhost:9000"),
    "http://localhost:9000/pay/1",
  );
  assert.equal(validatePaymentRedirect("http://localhost:9000/pay/1", ""), null);
});
