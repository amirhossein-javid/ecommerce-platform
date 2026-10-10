import assert from "node:assert/strict";
import test from "node:test";

import {
  getCartItemCount,
  isCart,
  isValidProductSlug,
  normalizeGuestCartToken,
  parseAddCartInput,
  parseCartItemId,
  parseQuantityInput,
} from "./cart-contract.ts";
import { formatToman, multiplyWholeRialPrice } from "./format-price.ts";

const validCart = {
  items: [
    {
      id: 7,
      product: {
        slug: "کفش-فوتسال-مدل-آلفا",
        name: "کفش فوتسال",
        price: "499001",
        primary_image: null,
      },
      quantity: 2,
      line_total: "998002",
      is_available: true,
      availability_reason: null,
    },
  ],
  subtotal: "998002",
};

test("accepts the exact Django cart shape and counts quantities", () => {
  assert.equal(isCart(validCart), true);
  assert.equal(getCartItemCount(validCart), 2);
  assert.equal(isCart({ ...validCart, subtotal: 998002 }), false);
});

test("validates Persian slugs and strict add input", () => {
  assert.equal(isValidProductSlug("کفش-فوتسال-مدل-آلفا"), true);
  assert.deepEqual(
    parseAddCartInput({ productSlug: "کفش-فوتسال", quantity: 1 }),
    { productSlug: "کفش-فوتسال", quantity: 1 },
  );
  assert.equal(
    parseAddCartInput({ productSlug: "کفش فوتسال", quantity: 1 }),
    null,
  );
  assert.equal(
    parseAddCartInput({ productSlug: "کفش-فوتسال", quantity: 1, admin: true }),
    null,
  );
});

test("rejects invalid item and quantity mutation inputs", () => {
  assert.deepEqual(parseQuantityInput({ quantity: 3 }), { quantity: 3 });
  assert.equal(parseQuantityInput({ quantity: 0 }), null);
  assert.equal(parseQuantityInput({ quantity: "3" }), null);
  assert.equal(parseQuantityInput({ quantity: 3, remove: true }), null);
  assert.equal(parseCartItemId("12"), 12);
  assert.equal(parseCartItemId("1.2"), null);
});

test("enforces the effective quantity limit and formats exact selected totals", () => {
  assert.deepEqual(parseQuantityInput({ quantity: 2_147_483_647 }), {
    quantity: 2_147_483_647,
  });
  assert.equal(parseQuantityInput({ quantity: 2_147_483_648 }), null);
  assert.equal(multiplyWholeRialPrice("499001", 3), "1497003");
  assert.equal(formatToman("1497003"), "۱۴۹٬۷۰۰ تومان و ۳ ریال");
  assert.equal(multiplyWholeRialPrice("invalid", 3), null);
});

test("accepts only canonical UUID-shaped guest credentials", () => {
  assert.equal(
    normalizeGuestCartToken("550E8400-E29B-41D4-A716-446655440000"),
    "550e8400-e29b-41d4-a716-446655440000",
  );
  assert.equal(normalizeGuestCartToken("not-a-token"), undefined);
});
