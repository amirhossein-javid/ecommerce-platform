import assert from "node:assert/strict";
import test from "node:test";

import {
  isCustomerAddressList,
  parseAddressId,
  parseAddressInput,
} from "./address-contract.ts";

const validInput = {
  title: "خانه",
  recipient_first_name: "علی",
  recipient_last_name: "احمدی",
  recipient_phone_number: "+989121234567",
  province: "تهران",
  city: "تهران",
  address: "خیابان آزادی، پلاک ۱۲",
  postal_code: "1234567890",
};

test("accepts and normalizes the exact Django address input", () => {
  assert.deepEqual(parseAddressInput({ ...validInput, title: "  خانه  " }), validInput);
});

test("rejects ownership injection and invalid shipping fields", () => {
  assert.equal(parseAddressInput({ ...validInput, is_default: true }), null);
  assert.equal(parseAddressInput({ ...validInput, customer_profile: 2 }), null);
  assert.equal(
    parseAddressInput({ ...validInput, recipient_phone_number: "09121234567" }),
    null,
  );
  assert.equal(parseAddressInput({ ...validInput, postal_code: "۱۲۳۴۵۶۷۸۹۰" }), null);
  assert.equal(parseAddressInput({ ...validInput, city: "" }), null);
});

test("accepts only safe positive address identifiers", () => {
  assert.equal(parseAddressId("12"), 12);
  assert.equal(parseAddressId("0"), null);
  assert.equal(parseAddressId("1/delete"), null);
  assert.equal(parseAddressId("9007199254740992"), null);
});

test("validates the unpaginated Django address list", () => {
  const address = {
    id: 1,
    ...validInput,
    is_default: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  assert.equal(isCustomerAddressList([address]), true);
  assert.equal(isCustomerAddressList({ results: [address] }), false);
  assert.equal(isCustomerAddressList([{ ...address, is_default: "yes" }]), false);
});
