import assert from "node:assert/strict";
import test from "node:test";

import { RefreshFailure } from "./refresh-failure.ts";

test("only a definitive refresh rejection invalidates a session", () => {
  assert.equal(new RefreshFailure(401).status, 401);
  assert.equal(new RefreshFailure(429).status, 429);
  for (const status of [undefined, 200, 400, 403, 500, 503]) {
    assert.equal(new RefreshFailure(status).status, 503);
  }
});

test("refresh Retry-After accepts seconds and canonical HTTP dates only", () => {
  const date = "Wed, 21 Oct 2037 07:28:00 GMT";
  for (const value of ["0", "60", date]) {
    assert.equal(new RefreshFailure(429, value).retryAfter, value);
  }
  for (const value of [undefined, null, "", "-1", "1.5", "Invalid Date", "private detail", "2037-10-21"]) {
    assert.equal(new RefreshFailure(429, value).retryAfter, undefined);
  }
  assert.equal(new RefreshFailure(503, "60").retryAfter, undefined);
});
