import assert from "node:assert/strict";
import test from "node:test";

import { createRefreshCoordinator } from "./refresh-coordinator.ts";

test("coalesces concurrent rotation and returns the same replacement tokens", async () => {
  let rotations = 0;
  let resolveRotation: ((value: { access: string; refresh: string }) => void) | undefined;
  const rotate = () => {
    rotations += 1;
    return new Promise<{ access: string; refresh: string }>((resolve) => {
      resolveRotation = resolve;
    });
  };
  const refresh = createRefreshCoordinator(
    rotate,
    (token) => `hash:${token}`,
    0,
  );

  const first = refresh("old-refresh", undefined);
  const second = refresh("old-refresh", undefined);
  assert.equal(rotations, 1);
  assert.equal(first, second);

  resolveRotation?.({ access: "new-access", refresh: "new-refresh" });
  assert.deepEqual(await first, { access: "new-access", refresh: "new-refresh" });
  assert.deepEqual(await second, { access: "new-access", refresh: "new-refresh" });
});

test("shares a failed rotation and permits a later retry after cleanup", async () => {
  let rotations = 0;
  const rotate = async () => {
    rotations += 1;
    throw new Error("invalid refresh");
  };
  const refresh = createRefreshCoordinator(
    rotate,
    (token) => `hash:${token}`,
    0,
  );

  const first = refresh("stale-refresh", undefined);
  const second = refresh("stale-refresh", undefined);
  assert.equal(rotations, 1);
  await assert.rejects(first, /invalid refresh/);
  await assert.rejects(second, /invalid refresh/);
  await new Promise((resolve) => setTimeout(resolve, 5));
  await assert.rejects(refresh("stale-refresh", undefined), /invalid refresh/);
  assert.equal(rotations, 2);
});

test("does not coalesce the same token across distinct client identities", async () => {
  let rotations = 0;
  const rotate = async (_refresh: string, clientIp: string) => {
    rotations += 1;
    return clientIp;
  };
  const refresh = createRefreshCoordinator(
    rotate,
    (token, clientIp) => `hash:${token}:${clientIp}`,
    0,
  );

  const first = refresh("shared-refresh", "203.0.113.10");
  const second = refresh("shared-refresh", "203.0.113.11");

  assert.equal(rotations, 2);
  assert.equal(await first, "203.0.113.10");
  assert.equal(await second, "203.0.113.11");
});
