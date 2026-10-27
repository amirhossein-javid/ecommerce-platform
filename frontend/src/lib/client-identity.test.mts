import assert from "node:assert/strict";
import test from "node:test";

import {
  forwardTrustedClientIp,
  TRUSTED_CLIENT_IP_HEADER,
  trustedClientIp,
} from "./client-identity.ts";

test("accepts only a single valid IP written by the trusted ingress", () => {
  assert.equal(
    trustedClientIp(new Headers({ [TRUSTED_CLIENT_IP_HEADER]: "203.0.113.10" })),
    "203.0.113.10",
  );
  assert.equal(
    trustedClientIp(new Headers({ [TRUSTED_CLIENT_IP_HEADER]: "2001:db8::10" })),
    "2001:db8::10",
  );
  assert.equal(
    trustedClientIp(
      new Headers({ [TRUSTED_CLIENT_IP_HEADER]: "198.51.100.1, 203.0.113.10" }),
    ),
    undefined,
  );
  assert.equal(
    trustedClientIp(new Headers({ [TRUSTED_CLIENT_IP_HEADER]: "client.example" })),
    undefined,
  );
});

test("does not trust browser-controlled standard forwarding headers", () => {
  assert.equal(
    trustedClientIp(
      new Headers({
        "x-forwarded-for": "198.51.100.1",
        "x-real-ip": "198.51.100.2",
      }),
    ),
    undefined,
  );
});

test("forwards only a validated trusted client identity", () => {
  const headers = new Headers({ [TRUSTED_CLIENT_IP_HEADER]: "198.51.100.200" });
  forwardTrustedClientIp(headers, "203.0.113.10");
  assert.equal(headers.get(TRUSTED_CLIENT_IP_HEADER), "203.0.113.10");

  forwardTrustedClientIp(headers, "not-an-ip");
  assert.equal(headers.has(TRUSTED_CLIENT_IP_HEADER), false);
});
