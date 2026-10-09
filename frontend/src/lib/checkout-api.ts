import "server-only";

import { cookies } from "next/headers";

import { fetchCustomerAddresses } from "@/lib/auth-api";
import { normalizeToken } from "@/lib/auth-contract";
import { ACCESS_COOKIE_NAME } from "@/lib/auth-security";
import { fetchCustomerCart } from "@/lib/cart-api";
import {
  type CheckoutOrder,
  isCheckoutOrder,
} from "@/lib/checkout-contract";

const CHECKOUT_PATH = "/api/v1/checkout/";
const ORDERS_PATH = "/api/v1/orders/";

export class CheckoutApiError extends Error {
  constructor(
    public readonly status?: number,
    public readonly payload?: unknown,
    public readonly retryAfter?: string | null,
    public readonly transportFailed = false,
  ) {
    super("The checkout API request failed.");
    this.name = "CheckoutApiError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;
  if (!value) throw new CheckoutApiError();
  try {
    return new URL(value);
  } catch {
    throw new CheckoutApiError();
  }
}

async function parsePayload(response: Response) {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

async function requestDjango(path: string, access: string, init: RequestInit) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${access}`);

  let response: Response;
  try {
    response = await fetch(new URL(path, getApiOrigin()), {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new CheckoutApiError(undefined, undefined, undefined, true);
  }

  if (!response.ok) {
    throw new CheckoutApiError(
      response.status,
      await parsePayload(response),
      response.headers.get("retry-after"),
    );
  }
  return response;
}

async function parseOrder(response: Response): Promise<CheckoutOrder> {
  const payload = await parsePayload(response);
  if (!isCheckoutOrder(payload)) {
    throw new CheckoutApiError(undefined, undefined, undefined, true);
  }
  return payload;
}

export async function checkoutCustomerCart(access: string, addressId: number) {
  return parseOrder(
    await requestDjango(CHECKOUT_PATH, access, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address_id: addressId }),
    }),
  );
}

export async function fetchCustomerOrder(access: string, orderId: number) {
  return parseOrder(
    await requestDjango(`${ORDERS_PATH}${orderId}/`, access, { method: "GET" }),
  );
}

export async function getCheckoutPageData() {
  const cookieStore = await cookies();
  const access = normalizeToken(cookieStore.get(ACCESS_COOKIE_NAME)?.value);
  if (!access) throw new CheckoutApiError(401);

  const [cart, addresses] = await Promise.all([
    fetchCustomerCart(access),
    fetchCustomerAddresses(access),
  ]);
  return { cart, addresses };
}

export async function getCustomerOrder(orderId: number) {
  const cookieStore = await cookies();
  const access = normalizeToken(cookieStore.get(ACCESS_COOKIE_NAME)?.value);
  if (!access) throw new CheckoutApiError(401);
  return fetchCustomerOrder(access, orderId);
}
