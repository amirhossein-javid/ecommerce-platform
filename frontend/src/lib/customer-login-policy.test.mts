import assert from "node:assert/strict";
import test from "node:test";

import type { CustomerProfile } from "./auth-contract.ts";
import { verifyStorefrontCustomer } from "./customer-login-policy.ts";

const tokens = { access: "new-access", refresh: "new-refresh" };
const profile: CustomerProfile = {
  id: 1,
  email: "customer@example.com",
  first_name: "مشتری",
  last_name: "فروشگاه",
  phone_number: "+989121234567",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

test("customer login verifies the profile without revoking valid tokens", async () => {
  let revoked = false;
  const result = await verifyStorefrontCustomer(
    tokens,
    async () => profile,
    async () => {
      revoked = true;
    },
  );

  assert.equal(result, profile);
  assert.equal(revoked, false);
});

test("admin-created user without a profile is rejected and refresh is revoked", async () => {
  const missingProfile = Object.assign(new Error("missing profile"), {
    status: 404,
  });
  let revokedRefresh = "";

  await assert.rejects(
    verifyStorefrontCustomer(
      tokens,
      async () => {
        throw missingProfile;
      },
      async (refresh) => {
        revokedRefresh = refresh;
      },
    ),
    (error) => error === missingProfile,
  );
  assert.equal(revokedRefresh, tokens.refresh);
});

test("upstream verification failure still attempts cleanup and keeps its identity", async () => {
  const upstreamFailure = Object.assign(new Error("upstream unavailable"), {
    status: 503,
  });
  let cleanupAttempts = 0;

  await assert.rejects(
    verifyStorefrontCustomer(
      tokens,
      async () => {
        throw upstreamFailure;
      },
      async () => {
        cleanupAttempts += 1;
        throw new Error("cleanup unavailable");
      },
    ),
    (error) => error === upstreamFailure,
  );
  assert.equal(cleanupAttempts, 1);
});
