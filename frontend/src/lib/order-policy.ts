import type { OrderStatus } from "./checkout-contract.ts";

export type OrderFailure =
  | "missing-profile"
  | "not-found"
  | "rate-limited"
  | "session-expired"
  | "upstream";

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  PENDING_PAYMENT: "در انتظار پرداخت",
  PAID: "پرداخت‌شده",
  PROCESSING: "در حال پردازش",
  SHIPPED: "ارسال‌شده",
  DELIVERED: "تحویل‌شده",
  CANCELLED: "لغوشده",
  EXPIRED: "منقضی‌شده",
};

export function classifyOrderFailure(status?: number, payload?: unknown): OrderFailure {
  const detail =
    payload && typeof payload === "object" && !Array.isArray(payload) &&
    "detail" in payload && typeof payload.detail === "string"
      ? payload.detail
      : undefined;
  if (status === 401 || status === 403) return "session-expired";
  if (status === 404) {
    return detail === "Customer profile not found." ? "missing-profile" : "not-found";
  }
  if (status === 429) return "rate-limited";
  return "upstream";
}

export function orderStatusTone(status: OrderStatus) {
  if (["PAID", "DELIVERED"].includes(status)) return "success";
  if (["CANCELLED", "EXPIRED"].includes(status)) return "destructive";
  return "primary";
}

