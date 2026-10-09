import "server-only";

import {
  type AuthTokens,
  type CustomerProfile,
  isAuthTokens,
  isCustomerProfile,
  type RegistrationInput,
} from "@/lib/auth-contract";

const LOGIN_PATH = "/api/v1/auth/login/";
const REGISTER_PATH = "/api/v1/auth/register/";
const REFRESH_PATH = "/api/v1/auth/token/refresh/";
const LOGOUT_PATH = "/api/v1/auth/logout/";
const PROFILE_PATH = "/api/v1/account/profile/";

export class AuthApiError extends Error {
  constructor(
    public readonly status?: number,
    public readonly payload?: unknown,
    public readonly retryAfter?: string | null,
  ) {
    super("The authentication API request failed.");
    this.name = "AuthApiError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;
  if (!value) {
    throw new AuthApiError();
  }

  try {
    return new URL(value);
  } catch {
    throw new AuthApiError();
  }
}

async function parsePayload(response: Response) {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

async function requestDjango(path: string, init: RequestInit) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(new URL(path, getApiOrigin()), {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new AuthApiError();
  }

  if (!response.ok) {
    throw new AuthApiError(
      response.status,
      await parsePayload(response),
      response.headers.get("retry-after"),
    );
  }

  return response;
}

async function requestTokens(path: string, body: unknown): Promise<AuthTokens> {
  const response = await requestDjango(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await parsePayload(response);
  if (!isAuthTokens(payload)) {
    throw new AuthApiError();
  }
  return payload;
}

export function loginCustomer(email: string, password: string) {
  return requestTokens(LOGIN_PATH, { email, password });
}

export async function registerCustomer(input: RegistrationInput) {
  await requestDjango(REGISTER_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function refreshCustomerTokens(refresh: string) {
  return requestTokens(REFRESH_PATH, { refresh });
}

export async function logoutCustomer(refresh: string) {
  await requestDjango(LOGOUT_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
}

export async function fetchCustomerProfile(
  access: string,
): Promise<CustomerProfile> {
  const response = await requestDjango(PROFILE_PATH, {
    method: "GET",
    headers: { Authorization: `Bearer ${access}` },
  });
  const payload = await parsePayload(response);
  if (!isCustomerProfile(payload)) {
    throw new AuthApiError();
  }
  return payload;
}
