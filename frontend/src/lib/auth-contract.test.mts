import assert from "node:assert/strict";
import test from "node:test";

import {
  isAuthTokens,
  isCustomerProfile,
  normalizeToken,
  parseLoginInput,
  parseProfileUpdateInput,
  parseRegistrationInput,
} from "./auth-contract.ts";

test("validates strict login input without changing the password", () => {
  assert.deepEqual(
    parseLoginInput({ email: " customer@example.com ", password: " pass word " }),
    { email: "customer@example.com", password: " pass word " },
  );
  assert.equal(parseLoginInput({ email: "bad", password: "secret" }), null);
  assert.equal(
    parseLoginInput({ email: "a@example.com", password: "secret", next: "//evil" }),
    null,
  );
});

test("accepts only the writable profile fields and preserves optional blanks", () => {
  assert.deepEqual(
    parseProfileUpdateInput({
      first_name: " علی ",
      last_name: " رضایی ",
      phone_number: " +989121234567 ",
    }),
    {
      first_name: "علی",
      last_name: "رضایی",
      phone_number: "+989121234567",
    },
  );
  assert.deepEqual(
    parseProfileUpdateInput({ first_name: "", last_name: "", phone_number: "" }),
    { first_name: "", last_name: "", phone_number: "" },
  );
  assert.equal(
    parseProfileUpdateInput({
      first_name: "علی",
      last_name: "رضایی",
      phone_number: "09121234567",
    }),
    null,
  );
  assert.equal(
    parseProfileUpdateInput({
      first_name: "علی",
      last_name: "رضایی",
      phone_number: "+989121234567",
      email: "attacker@example.com",
    }),
    null,
  );
});

test("validates registration names and canonical E.164 phone numbers", () => {
  assert.deepEqual(
    parseRegistrationInput({
      email: "user@example.com",
      password: "strong-password",
      first_name: " علی ",
      last_name: " رضایی ",
      phone_number: "+989121234567",
    }),
    {
      email: "user@example.com",
      password: "strong-password",
      first_name: "علی",
      last_name: "رضایی",
      phone_number: "+989121234567",
    },
  );
  assert.equal(
    parseRegistrationInput({
      email: "user@example.com",
      password: "strong-password",
      first_name: "علی",
      last_name: "رضایی",
      phone_number: "09121234567",
    }),
    null,
  );
});

test("accepts only bounded token pairs and the public profile shape", () => {
  assert.equal(isAuthTokens({ access: "access-token", refresh: "refresh-token" }), true);
  assert.equal(isAuthTokens({ access: "access-token", refresh: "refresh-token", admin: true }), false);
  assert.equal(normalizeToken(""), null);
  assert.equal(
    isCustomerProfile({
      id: 1,
      email: "user@example.com",
      first_name: "علی",
      last_name: "رضایی",
      phone_number: "+989121234567",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    }),
    true,
  );
});
