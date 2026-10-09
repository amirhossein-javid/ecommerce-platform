import assert from "node:assert/strict";
import test from "node:test";

import {
  ACCESS_COOKIE_MAX_AGE,
  getAuthCookieOptions,
  REFRESH_COOKIE_MAX_AGE,
} from "./auth-security.ts";
import { isTrustedMutationRequest } from "./cart-security.ts";

test("authentication cookies are HttpOnly and follow Django token lifetimes", () => {
  const access = getAuthCookieOptions("access", true);
  const refresh = getAuthCookieOptions("refresh", true);

  assert.equal(access.httpOnly, true);
  assert.equal(access.secure, true);
  assert.equal(access.sameSite, "lax");
  assert.equal(access.path, "/");
  assert.equal(access.maxAge, ACCESS_COOKIE_MAX_AGE);
  assert.equal(refresh.maxAge, REFRESH_COOKIE_MAX_AGE);
  assert.equal("domain" in refresh, false);
  assert.equal(getAuthCookieOptions("refresh", false).secure, false);
});

test("authentication mutations use the established exact-origin protection", () => {
  assert.equal(
    isTrustedMutationRequest(
      "https://shop.example/api/auth/login",
      new Headers({
        host: "shop.example",
        origin: "https://shop.example",
        "sec-fetch-site": "same-origin",
      }),
    ),
    true,
  );
  assert.equal(
    isTrustedMutationRequest(
      "https://shop.example/api/auth/logout",
      new Headers({
        host: "shop.example",
        origin: "https://evil.example",
        "sec-fetch-site": "cross-site",
      }),
    ),
    false,
  );
});
