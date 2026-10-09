import "server-only";

import { cookies } from "next/headers";

import { AuthApiError } from "@/lib/auth-api";
import { type AuthTokens, normalizeToken } from "@/lib/auth-contract";
import { refreshSession } from "@/lib/auth-refresh";
import {
  ACCESS_COOKIE_NAME,
  REFRESH_COOKIE_NAME,
} from "@/lib/auth-security";

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

function isAuthenticationError(error: unknown) {
  return (
    error instanceof AuthApiError &&
    (error.status === 401 || error.status === 403)
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
      if (!isAuthenticationError(error)) {
        throw error;
      }
    }
  }

  if (!refresh) {
    throw new AuthSessionError();
  }

  let tokens: AuthTokens;
  try {
    tokens = await refreshSession(refresh);
  } catch {
    throw new AuthSessionError();
  }

  try {
    return { value: await operation(tokens.access), rotatedTokens: tokens };
  } catch (error) {
    if (isAuthenticationError(error)) {
      throw new AuthSessionError();
    }
    throw new AuthenticatedOperationError(error, tokens);
  }
}
