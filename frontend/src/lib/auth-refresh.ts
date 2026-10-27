import "server-only";

import { createHash } from "node:crypto";

import { AuthApiError, refreshCustomerTokens } from "@/lib/auth-api";
import type { AuthTokens } from "@/lib/auth-contract";
import { createRefreshCoordinator } from "@/lib/refresh-coordinator";
import { RefreshFailure } from "@/lib/refresh-failure";

function refreshKey(refresh: string, clientIp?: string) {
  return `${createHash("sha256").update(refresh).digest("hex")}:${clientIp ?? "unknown"}`;
}

export const refreshSession = createRefreshCoordinator<
  AuthTokens,
  string | undefined
>(
  async (refresh, clientIp) => {
    try {
      return await refreshCustomerTokens(refresh, clientIp);
    } catch (error) {
      // Never retry here: a lost response may have followed token rotation.
      throw new RefreshFailure(
        error instanceof AuthApiError ? error.status : undefined,
        error instanceof AuthApiError ? error.retryAfter : undefined,
      );
    }
  },
  refreshKey,
);
