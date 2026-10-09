import assert from "node:assert/strict";
import test from "node:test";

import {
  isCheckoutOrder,
  parseCheckoutInput,
  parseOrderId,
} from "./checkout-contract.ts";

const order = {
  id: 14,
  status: "PENDING_PAYMENT",
  subtotal: "120001",
  discount_total: "0",
  shipping_total: "0",
  grand_total: "120001",
  shipping_title: "خانه",
  shipping_recipient_first_name: "علی",
  shipping_recipient_last_name: "احمدی",
  shipping_recipient_phone_number: "+989121234567",
  shipping_province: "تهران",
  shipping_city: "تهران",
  shipping_address: "خیابان آزادی",
  shipping_postal_code: "1234567890",
  items: [
    {
      id: 4,
      product_name: "محصول",
      sku: "SKU-1",
      unit_price: "120001",
      quantity: 1,
      line_total: "120001",
    },
  ],
  created_at: "2026-10-10T10:00:00Z",
  payment_expires_at: "2026-10-10T10:15:00Z",
};

test("accepts the authoritative checkout order response", () => {
  assert.equal(isCheckoutOrder(order), true);
  assert.equal(isCheckoutOrder({ ...order, grand_total: 12.5 }), false);
  assert.equal(isCheckoutOrder({ ...order, status: "PAID_BY_CLIENT" }), false);
});

test("accepts the order-detail shape without reservation expiry", () => {
  const detail: Record<string, unknown> = { ...order };
  delete detail.payment_expires_at;
  assert.equal(isCheckoutOrder({ ...detail, updated_at: order.created_at }), true);
});

test("strictly validates checkout and order identifiers", () => {
  assert.deepEqual(parseCheckoutInput({ addressId: 7 }), { addressId: 7 });
  assert.equal(parseCheckoutInput({ addressId: "7" }), null);
  assert.equal(parseCheckoutInput({ addressId: 7, total: "1" }), null);
  assert.equal(parseCheckoutInput({}), null);
  assert.equal(parseOrderId("7"), 7);
  assert.equal(parseOrderId("0"), null);
  assert.equal(parseOrderId("7x"), null);
});
