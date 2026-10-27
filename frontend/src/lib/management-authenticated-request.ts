import "server-only";

import { cookies, headers } from "next/headers";

import type { AuthTokens } from "@/lib/auth-contract";
import { normalizeToken } from "@/lib/auth-contract";
import { refreshSession } from "@/lib/auth-refresh";
import { RefreshFailure } from "@/lib/refresh-failure";
import {
  MANAGEMENT_ACCESS_COOKIE_NAME,
  MANAGEMENT_REFRESH_COOKIE_NAME,
} from "@/lib/management-auth-security";
import { trustedClientIp } from "@/lib/client-identity";

export class ManagementSessionError extends Error {
  constructor() {
    super("The management session is missing or expired.");
    this.name = "ManagementSessionError";
  }
}

export class ManagementOperationError extends Error {
  constructor(
    public readonly originalError: unknown,
    public readonly rotatedTokens: AuthTokens,
  ) {
    super("The management operation failed after token rotation.");
    this.name = "ManagementOperationError";
  }
}

function isManagementAuthenticationFailure(error: unknown) {
  if (!error || typeof error !== "object" || !("status" in error)) return false;
  return error.status === 401;
}

export async function withManagementSession<T>(
  operation: (access: string) => Promise<T>,
): Promise<{ value: T; rotatedTokens?: AuthTokens }> {
  const cookieStore = await cookies();
  const access = normalizeToken(
    cookieStore.get(MANAGEMENT_ACCESS_COOKIE_NAME)?.value,
  );
  const refresh = normalizeToken(
    cookieStore.get(MANAGEMENT_REFRESH_COOKIE_NAME)?.value,
  );

  if (access) {
    try {
      return { value: await operation(access) };
    } catch (error) {
      if (!isManagementAuthenticationFailure(error)) throw error;
    }
  }
  if (!refresh) throw new ManagementSessionError();

  let tokens: AuthTokens;
  try {
    tokens = await refreshSession(refresh, trustedClientIp(await headers()));
  } catch (error) {
    if (error instanceof RefreshFailure && error.status === 401) {
      throw new ManagementSessionError();
    }
    throw error;
  }
  try {
    return { value: await operation(tokens.access), rotatedTokens: tokens };
  } catch (error) {
    if (isManagementAuthenticationFailure(error)) {
      throw new ManagementSessionError();
    }
    throw new ManagementOperationError(error, tokens);
  }
}
