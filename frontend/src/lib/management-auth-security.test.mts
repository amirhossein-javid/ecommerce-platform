import assert from "node:assert/strict";
import test from "node:test";

import { ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME } from "./auth-security.ts";
import {
  getManagementCookieOptions,
  MANAGEMENT_ACCESS_COOKIE_NAME,
  MANAGEMENT_REFRESH_COOKIE_NAME,
} from "./management-auth-security.ts";

test("management sessions use separate secure HttpOnly cookies", () => {
  assert.notEqual(MANAGEMENT_ACCESS_COOKIE_NAME, ACCESS_COOKIE_NAME);
  assert.notEqual(MANAGEMENT_REFRESH_COOKIE_NAME, REFRESH_COOKIE_NAME);
  assert.deepEqual(getManagementCookieOptions("access", true), {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 5,
  });
  assert.equal(
    getManagementCookieOptions("refresh", false).maxAge,
    60 * 60 * 24 * 7,
  );
});
