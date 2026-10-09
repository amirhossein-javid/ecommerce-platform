import assert from "node:assert/strict";
import test from "node:test";

import {
  getGuestCartCookieOptions,
  hasJsonContentType,
  isTrustedMutationRequest,
} from "./cart-security.ts";

test("guest cookie is HttpOnly, same-site, path scoped, and Secure in production", () => {
  const production = getGuestCartCookieOptions(true);
  const development = getGuestCartCookieOptions(false);

  assert.equal(production.httpOnly, true);
  assert.equal(production.secure, true);
  assert.equal(production.sameSite, "lax");
  assert.equal(production.path, "/");
  assert.equal("domain" in production, false);
  assert.equal(development.secure, false);
});

test("mutation origin protection accepts only the exact storefront origin", () => {
  const sameOrigin = new Headers({
    host: "shop.example",
    origin: "https://shop.example",
    "sec-fetch-site": "same-origin",
  });
  const crossOrigin = new Headers({
    origin: "https://attacker.example",
    "sec-fetch-site": "cross-site",
  });

  assert.equal(
    isTrustedMutationRequest(
      "https://shop.example/api/cart/items",
      sameOrigin,
    ),
    true,
  );
  assert.equal(
    isTrustedMutationRequest(
      "http://frontend:3000/api/cart/items",
      new Headers({
        host: "localhost:3000",
        origin: "http://localhost:3000",
        "sec-fetch-site": "same-origin",
      }),
    ),
    true,
  );
  assert.equal(
    isTrustedMutationRequest(
      "https://shop.example/api/cart/items",
      crossOrigin,
    ),
    false,
  );
  assert.equal(
    isTrustedMutationRequest(
      "https://shop.example/api/cart/items",
      new Headers(),
    ),
    false,
  );
});

test("JSON mutations require an application/json content type", () => {
  assert.equal(
    hasJsonContentType(
      new Headers({ "content-type": "application/json; charset=utf-8" }),
    ),
    true,
  );
  assert.equal(
    hasJsonContentType(
      new Headers({ "content-type": "application/x-www-form-urlencoded" }),
    ),
    false,
  );
  assert.equal(
    hasJsonContentType(new Headers({ "content-type": "application/jsonp" })),
    false,
  );
});
