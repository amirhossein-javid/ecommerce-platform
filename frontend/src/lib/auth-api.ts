import "server-only";

import {
  type AuthTokens,
  type CustomerProfile,
  isAuthTokens,
  isCustomerProfile,
  type ProfileUpdateInput,
  type RegistrationInput,
} from "@/lib/auth-contract";
import {
  type AddressInput,
  type CustomerAddress,
  isCustomerAddress,
  isCustomerAddressList,
} from "@/lib/address-contract";
import { forwardTrustedClientIp } from "@/lib/client-identity";

const LOGIN_PATH = "/api/v1/auth/login/";
const REGISTER_PATH = "/api/v1/auth/register/";
const REFRESH_PATH = "/api/v1/auth/token/refresh/";
const LOGOUT_PATH = "/api/v1/auth/logout/";
const PROFILE_PATH = "/api/v1/account/profile/";
const ADDRESSES_PATH = "/api/v1/account/addresses/";

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

async function requestDjango(
  path: string,
  init: RequestInit,
  clientIp?: string,
) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  forwardTrustedClientIp(headers, clientIp);

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

async function requestTokens(
  path: string,
  body: unknown,
  clientIp?: string,
): Promise<AuthTokens> {
  const response = await requestDjango(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, clientIp);
  const payload = await parsePayload(response);
  if (!isAuthTokens(payload)) {
    throw new AuthApiError();
  }
  return payload;
}

export function loginCustomer(email: string, password: string, clientIp?: string) {
  return requestTokens(LOGIN_PATH, { email, password }, clientIp);
}

export async function registerCustomer(input: RegistrationInput, clientIp?: string) {
  await requestDjango(REGISTER_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }, clientIp);
}

export function refreshCustomerTokens(refresh: string, clientIp?: string) {
  return requestTokens(REFRESH_PATH, { refresh }, clientIp);
}

export async function logoutCustomer(refresh: string, clientIp?: string) {
  await requestDjango(LOGOUT_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  }, clientIp);
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

export async function updateCustomerProfile(
  access: string,
  input: ProfileUpdateInput,
): Promise<CustomerProfile> {
  const response = await requestDjango(PROFILE_PATH, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${access}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  const payload = await parsePayload(response);
  if (!isCustomerProfile(payload)) {
    throw new AuthApiError();
  }
  return payload;
}

export async function fetchCustomerAddresses(
  access: string,
): Promise<CustomerAddress[]> {
  const response = await requestDjango(ADDRESSES_PATH, {
    method: "GET",
    headers: { Authorization: `Bearer ${access}` },
  });
  const payload = await parsePayload(response);
  if (!isCustomerAddressList(payload)) throw new AuthApiError();
  return payload;
}

async function requestAddress(
  path: string,
  access: string,
  init: RequestInit,
): Promise<CustomerAddress> {
  const response = await requestDjango(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${access}`,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  const payload = await parsePayload(response);
  if (!isCustomerAddress(payload)) throw new AuthApiError();
  return payload;
}

export function createCustomerAddress(access: string, input: AddressInput) {
  return requestAddress(ADDRESSES_PATH, access, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateCustomerAddress(
  access: string,
  id: number,
  input: AddressInput,
) {
  return requestAddress(`${ADDRESSES_PATH}${id}/`, access, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function deleteCustomerAddress(access: string, id: number) {
  await requestDjango(`${ADDRESSES_PATH}${id}/`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${access}` },
  });
}

export function setDefaultCustomerAddress(access: string, id: number) {
  return requestAddress(`${ADDRESSES_PATH}${id}/set-default/`, access, {
    method: "POST",
  });
}
