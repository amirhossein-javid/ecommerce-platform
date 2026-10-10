import assert from "node:assert/strict";
import test from "node:test";

import { isCustomerOrderPage, parseOrderPage } from "./order-contract.ts";
import { classifyOrderFailure, ORDER_STATUS_LABELS } from "./order-policy.ts";

const summary = {
  id: 9,
  status: "PENDING_PAYMENT",
  subtotal: "250000",
  discount_total: "0",
  shipping_total: "0",
  grand_total: "250000",
  items: [{ product_name: "کالا", sku: "SKU-1", unit_price: "250000", quantity: 1, line_total: "250000" }],
  created_at: "2026-10-10T10:00:00Z",
  updated_at: "2026-10-10T10:00:00Z",
};

test("validates the paginated owned-order list contract", () => {
  assert.equal(isCustomerOrderPage({ count: 1, next: null, previous: null, results: [summary] }), true);
  assert.equal(isCustomerOrderPage({ count: 1, next: null, previous: null, results: [{ ...summary, status: "UNKNOWN" }] }), false);
  assert.equal(isCustomerOrderPage({ count: 1, next: null, previous: null, results: [{ ...summary, items: [{ ...summary.items[0], line_total: 12 }] }] }), false);
});

test("maps every backend status to a Persian label", () => {
  assert.deepEqual(Object.keys(ORDER_STATUS_LABELS).sort(), ["CANCELLED", "DELIVERED", "EXPIRED", "PAID", "PENDING_PAYMENT", "PROCESSING", "SHIPPED"].sort());
});

test("keeps ownership, session, throttling and upstream errors distinct", () => {
  assert.equal(classifyOrderFailure(401), "session-expired");
  assert.equal(classifyOrderFailure(404, { detail: "Not found." }), "not-found");
  assert.equal(classifyOrderFailure(404, { detail: "Customer profile not found." }), "missing-profile");
  assert.equal(classifyOrderFailure(429), "rate-limited");
  assert.equal(classifyOrderFailure(503), "upstream");
});

test("normalizes invalid page input without forwarding arbitrary query values", () => {
  assert.equal(parseOrderPage("3"), 3);
  assert.equal(parseOrderPage("0"), 1);
  assert.equal(parseOrderPage("1&status=PAID"), 1);
  assert.equal(parseOrderPage(undefined), 1);
});

