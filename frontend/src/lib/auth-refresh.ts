import "server-only";

import { createHash } from "node:crypto";

import { refreshCustomerTokens } from "@/lib/auth-api";
import type { AuthTokens } from "@/lib/auth-contract";
import { createRefreshCoordinator } from "@/lib/refresh-coordinator";

function refreshKey(refresh: string, clientIp?: string) {
  return `${createHash("sha256").update(refresh).digest("hex")}:${clientIp ?? "unknown"}`;
}

export const refreshSession = createRefreshCoordinator<
  AuthTokens,
  string | undefined
>(
  refreshCustomerTokens,
  refreshKey,
);
