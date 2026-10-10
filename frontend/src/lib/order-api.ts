import "server-only";

import { cookies } from "next/headers";

import { normalizeToken } from "@/lib/auth-contract";
import { ACCESS_COOKIE_NAME } from "@/lib/auth-security";
import {
  isCustomerOrderDetail,
  isCustomerOrderPage,
  type CustomerOrderDetail,
  type CustomerOrderPage,
} from "@/lib/order-contract";

const ORDERS_PATH = "/api/v1/orders/";

export class OrderApiError extends Error {
  constructor(
    public readonly status?: number,
    public readonly payload?: unknown,
    public readonly retryAfter?: string | null,
  ) {
    super("The order API request failed.");
    this.name = "OrderApiError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;
  if (!value) throw new OrderApiError();
  try {
    return new URL(value);
  } catch {
    throw new OrderApiError();
  }
}

async function parsePayload(response: Response) {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

async function requestDjango(path: string, access: string) {
  let response: Response;
  try {
    response = await fetch(new URL(path, getApiOrigin()), {
      headers: { Accept: "application/json", Authorization: `Bearer ${access}` },
      cache: "no-store",
    });
  } catch {
    throw new OrderApiError();
  }
  if (!response.ok) {
    throw new OrderApiError(
      response.status,
      await parsePayload(response),
      response.headers.get("retry-after"),
    );
  }
  return response;
}

export async function fetchCustomerOrders(access: string, page: number): Promise<CustomerOrderPage> {
  const response = await requestDjango(`${ORDERS_PATH}?page=${page}`, access);
  const payload = await parsePayload(response);
  if (!isCustomerOrderPage(payload)) throw new OrderApiError();
  return payload;
}

export async function fetchCustomerOrderDetail(
  access: string,
  orderId: number,
): Promise<CustomerOrderDetail> {
  const response = await requestDjango(`${ORDERS_PATH}${orderId}/`, access);
  const payload = await parsePayload(response);
  if (!isCustomerOrderDetail(payload)) throw new OrderApiError();
  return payload;
}

async function accessToken() {
  return normalizeToken((await cookies()).get(ACCESS_COOKIE_NAME)?.value);
}

export async function getCustomerOrders(page: number) {
  const access = await accessToken();
  if (!access) throw new OrderApiError(401);
  return fetchCustomerOrders(access, page);
}

export async function getCustomerOrderDetail(orderId: number) {
  const access = await accessToken();
  if (!access) throw new OrderApiError(401);
  return fetchCustomerOrderDetail(access, orderId);
}

