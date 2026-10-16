import assert from "node:assert/strict";
import test from "node:test";

import {
  isManagementOrderDetail,
  isManagementSummary,
  parseShipment,
  parseTransition,
} from "./management-order-contract.ts";

test("validates authoritative dashboard metrics", () => {
  assert.equal(isManagementSummary({ order_count: 4, successful_revenue: "12000", pending_fulfillment_count: 2, low_stock_product_count: 1, low_stock_threshold: 5 }), true);
  assert.equal(isManagementSummary({ order_count: 4, successful_revenue: 12000, pending_fulfillment_count: 2, low_stock_product_count: 1, low_stock_threshold: 5 }), false);
});

test("accepts only explicit fulfillment transitions", () => {
  assert.deepEqual(parseTransition({ status: "SHIPPED" }), { status: "SHIPPED" });
  assert.equal(parseTransition({ status: "PAID" }), null);
  assert.equal(parseTransition({ status: "SHIPPED", force: true }), null);
});

test("normalizes complete shipment data", () => {
  assert.deepEqual(parseShipment({ carrier: "  پست  ", tracking_number: " X-1 " }), { carrier: "پست", tracking_number: "X-1" });
  assert.equal(parseShipment({ carrier: "", tracking_number: "X" }), null);
});

test("validates management order details", () => {
  const value = {
    id: 1, status: "PROCESSING", refund_status: "NOT_REQUIRED", customer_display_name: "سارا اکبری", item_count: 2,
    grand_total: "1000", created_at: "2026-10-10T10:00:00Z", updated_at: "2026-10-10T10:00:00Z",
    customer_email: "sara@example.com", subtotal: "1000", discount_total: "0", shipping_total: "0", shipping_title: "خانه",
    shipping_recipient_first_name: "سارا", shipping_recipient_last_name: "اکبری", shipping_recipient_phone_number: "+989121234567",
    shipping_province: "اصفهان", shipping_city: "اصفهان", shipping_address: "نشانی", shipping_postal_code: "1234567890",
    paid_at: "2026-10-10T10:00:00Z", processing_at: null, shipped_at: null, delivered_at: null, cancelled_at: null, refund_resolved_at: null,
    items: [{ id: 2, product_name: "گلدان", sku: "VASE", unit_price: "500", quantity: 2, line_total: "1000" }],
    shipment: { carrier: "", tracking_number: "", created_at: "2026-10-10T10:00:00Z", updated_at: "2026-10-10T10:00:00Z" },
    status_history: [{ from_status: "PAID", to_status: "PROCESSING", actor_type: "OPERATOR", actor_display_name: "op@example.com", created_at: "2026-10-10T10:00:00Z" }],
  };
  assert.equal(isManagementOrderDetail(value), true);
  assert.equal(isManagementOrderDetail({ ...value, grand_total: 1000 }), false);
});
