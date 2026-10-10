import { isOrderStatus, type OrderStatus } from "./checkout-contract.ts";

const WHOLE_RIAL_PATTERN = /^\d+$/;
const PAYMENT_STATUSES = ["PENDING", "SUCCESS", "FAILED"] as const;

export type PaymentStatus = (typeof PAYMENT_STATUSES)[number];

export type PaymentAttempt = {
  id: number;
  status: PaymentStatus;
  amount: string;
  currency: "IRR";
  payment_url: string | null;
  payment_identifier: string | null;
  created_at: string;
  updated_at: string;
};

type JsonPrimitive = string | number | boolean | null;
export type CallbackData = {
  [key: string]: JsonPrimitive | JsonPrimitive[] | CallbackData;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}

function isDateTime(value: unknown) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

export function isPaymentAttempt(value: unknown): value is PaymentAttempt {
  if (!isRecord(value)) return false;
  const paymentUrl = value.payment_url;
  const identifier = value.payment_identifier;

  return (
    isPositiveInteger(value.id) &&
    typeof value.status === "string" &&
    (PAYMENT_STATUSES as readonly string[]).includes(value.status) &&
    typeof value.amount === "string" &&
    WHOLE_RIAL_PATTERN.test(value.amount) &&
    value.currency === "IRR" &&
    (paymentUrl === null || typeof paymentUrl === "string") &&
    (identifier === null ||
      (typeof identifier === "string" && identifier.length > 0 && identifier.length <= 255)) &&
    !(paymentUrl && identifier) &&
    isDateTime(value.created_at) &&
    isDateTime(value.updated_at)
  );
}

export function parsePaymentAttempt(value: unknown): PaymentAttempt | null {
  if (!isPaymentAttempt(value)) return null;
  return {
    id: value.id,
    status: value.status,
    amount: value.amount,
    currency: value.currency,
    payment_url: value.payment_url,
    payment_identifier: value.payment_identifier,
    created_at: value.created_at,
    updated_at: value.updated_at,
  };
}

export function parsePositiveId(value: string) {
  if (!/^[1-9][0-9]*$/.test(value)) return null;
  const id = Number(value);
  return isPositiveInteger(id) ? id : null;
}

export function parseEmptyPaymentInput(value: unknown) {
  return isRecord(value) && Object.keys(value).length === 0 ? {} : null;
}

function isSafeJsonValue(value: unknown, depth: number): boolean {
  if (value === null || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "string") return value.length <= 2_000;
  if (depth >= 3) return false;
  if (Array.isArray(value)) {
    return value.length <= 20 && value.every((item) => isSafeJsonValue(item, depth + 1));
  }
  if (!isRecord(value) || Object.keys(value).length > 50) return false;
  return Object.entries(value).every(
    ([key, item]) => key.length > 0 && key.length <= 100 && isSafeJsonValue(item, depth + 1),
  );
}

export function parseVerificationInput(value: unknown): { callbackData: CallbackData } | null {
  if (!isRecord(value) || Object.keys(value).length !== 1 || !("callbackData" in value)) {
    return null;
  }
  if (!isRecord(value.callbackData) || !isSafeJsonValue(value.callbackData, 0)) {
    return null;
  }
  try {
    if (JSON.stringify(value.callbackData).length > 16_384) return null;
  } catch {
    return null;
  }
  return { callbackData: value.callbackData as CallbackData };
}

export function isPayableOrderStatus(status: OrderStatus) {
  return status === "PENDING_PAYMENT";
}

export function isTerminalPaymentOrderStatus(status: unknown): status is OrderStatus {
  return isOrderStatus(status) && ["PAID", "CANCELLED", "EXPIRED"].includes(status);
}
