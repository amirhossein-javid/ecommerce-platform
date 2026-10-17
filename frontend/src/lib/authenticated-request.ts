import "server-only";

import { cookies, headers } from "next/headers";

import { type AuthTokens, normalizeToken } from "@/lib/auth-contract";
import { isAuthenticationFailure } from "@/lib/auth-error-policy";
import { refreshSession } from "@/lib/auth-refresh";
import {
  ACCESS_COOKIE_NAME,
  REFRESH_COOKIE_NAME,
} from "@/lib/auth-security";
import { trustedClientIp } from "@/lib/client-identity";

export class AuthSessionError extends Error {
  constructor() {
    super("The customer session is missing or expired.");
    this.name = "AuthSessionError";
  }
}

export class AuthenticatedOperationError extends Error {
  constructor(
    public readonly originalError: unknown,
    public readonly rotatedTokens: AuthTokens,
  ) {
    super("The authenticated operation failed after token rotation.");
    this.name = "AuthenticatedOperationError";
  }
}

export async function hasAuthenticationCookies() {
  const cookieStore = await cookies();
  return Boolean(
    cookieStore.get(ACCESS_COOKIE_NAME)?.value ||
      cookieStore.get(REFRESH_COOKIE_NAME)?.value,
  );
}

export async function withAuthenticatedSession<T>(
  operation: (access: string) => Promise<T>,
): Promise<{ value: T; rotatedTokens?: AuthTokens }> {
  const cookieStore = await cookies();
  const access = normalizeToken(cookieStore.get(ACCESS_COOKIE_NAME)?.value);
  const refresh = normalizeToken(cookieStore.get(REFRESH_COOKIE_NAME)?.value);

  if (access) {
    try {
      return { value: await operation(access) };
    } catch (error) {
      if (!isAuthenticationFailure(error)) {
        throw error;
      }
    }
  }

  if (!refresh) {
    throw new AuthSessionError();
  }

  let tokens: AuthTokens;
  try {
    tokens = await refreshSession(refresh, trustedClientIp(await headers()));
  } catch {
    throw new AuthSessionError();
  }

  try {
    return { value: await operation(tokens.access), rotatedTokens: tokens };
  } catch (error) {
    if (isAuthenticationFailure(error)) {
      throw new AuthSessionError();
    }
    throw new AuthenticatedOperationError(error, tokens);
  }
}
