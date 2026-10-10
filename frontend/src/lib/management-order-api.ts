import "server-only";

import {
  isManagementOrderDetail,
  isManagementOrderPage,
  isManagementSummary,
  type ManagementOrderDetail,
  type ManagementOrderPage,
  type ManagementSummary,
} from "@/lib/management-order-contract";

const ROOT = "/api/v1/management/";

export class ManagementOrderApiError extends Error {
  constructor(public readonly status?: number, public readonly payload?: unknown) {
    super("The order management API request failed.");
    this.name = "ManagementOrderApiError";
  }
}

function origin() {
  const value = process.env.DJANGO_API_URL;
  if (!value) throw new ManagementOrderApiError();
  try { return new URL(value); } catch { throw new ManagementOrderApiError(); }
}

async function payload(response: Response) {
  try { return await response.json() as unknown; } catch { return undefined; }
}

async function request(path: string, access: string, init: RequestInit) {
  let response: Response;
  try {
    response = await fetch(new URL(path, origin()), {
      ...init,
      headers: { Accept: "application/json", Authorization: `Bearer ${access}`, ...init.headers },
      cache: "no-store",
    });
  } catch { throw new ManagementOrderApiError(); }
  if (!response.ok) throw new ManagementOrderApiError(response.status, await payload(response));
  return response;
}

export async function fetchManagementSummary(access: string): Promise<ManagementSummary> {
  const value = await payload(await request(`${ROOT}dashboard/summary/`, access, { method: "GET" }));
  if (!isManagementSummary(value)) throw new ManagementOrderApiError();
  return value;
}

export async function fetchManagementOrders(access: string, query = ""): Promise<ManagementOrderPage> {
  const value = await payload(await request(`${ROOT}orders/${query}`, access, { method: "GET" }));
  if (!isManagementOrderPage(value)) throw new ManagementOrderApiError();
  return value;
}

export async function fetchManagementOrder(access: string, id: number): Promise<ManagementOrderDetail> {
  const value = await payload(await request(`${ROOT}orders/${id}/`, access, { method: "GET" }));
  if (!isManagementOrderDetail(value)) throw new ManagementOrderApiError();
  return value;
}

async function orderMutation(access: string, id: number, path: string, init: RequestInit) {
  const value = await payload(await request(`${ROOT}orders/${id}/${path}`, access, init));
  if (!isManagementOrderDetail(value)) throw new ManagementOrderApiError();
  return value;
}

export function transitionManagementOrder(access: string, id: number, status: string) {
  return orderMutation(access, id, "transition/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
}

export function updateManagementShipment(access: string, id: number, carrier: string, tracking_number: string) {
  return orderMutation(access, id, "shipment/", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ carrier, tracking_number }) });
}

export function resolveManagementRefund(access: string, id: number) {
  return orderMutation(access, id, "resolve-refund/", { method: "POST" });
}
