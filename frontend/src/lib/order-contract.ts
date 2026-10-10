import {
  isCheckoutOrder,
  isOrderStatus,
  type CheckoutOrder,
  type CheckoutOrderItem,
  type OrderStatus,
} from "./checkout-contract.ts";

const WHOLE_RIAL_PATTERN = /^\d+$/;

export type CustomerOrderSummary = {
  id: number;
  status: OrderStatus;
  subtotal: string;
  discount_total: string;
  shipping_total: string;
  grand_total: string;
  items: CheckoutOrderItem[];
  created_at: string;
  updated_at: string;
};

export type CustomerOrderDetail = CheckoutOrder;

export type CustomerOrderPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: CustomerOrderSummary[];
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

function isMoney(value: unknown): value is string {
  return typeof value === "string" && WHOLE_RIAL_PATTERN.test(value);
}

function isOrderItem(value: unknown): value is CheckoutOrderItem {
  if (!isRecord(value)) return false;
  return (
    (value.id === undefined || isPositiveInteger(value.id)) &&
    typeof value.product_name === "string" &&
    typeof value.sku === "string" &&
    isMoney(value.unit_price) &&
    isPositiveInteger(value.quantity) &&
    isMoney(value.line_total)
  );
}

export function isCustomerOrderSummary(value: unknown): value is CustomerOrderSummary {
  if (!isRecord(value)) return false;
  return (
    isPositiveInteger(value.id) &&
    isOrderStatus(value.status) &&
    isMoney(value.subtotal) &&
    isMoney(value.discount_total) &&
    isMoney(value.shipping_total) &&
    isMoney(value.grand_total) &&
    Array.isArray(value.items) &&
    value.items.every(isOrderItem) &&
    isDateTime(value.created_at) &&
    isDateTime(value.updated_at)
  );
}

export function isCustomerOrderPage(value: unknown): value is CustomerOrderPage {
  if (!isRecord(value)) return false;
  return (
    Number.isSafeInteger(value.count) &&
    Number(value.count) >= 0 &&
    (value.next === null || typeof value.next === "string") &&
    (value.previous === null || typeof value.previous === "string") &&
    Array.isArray(value.results) &&
    value.results.every(isCustomerOrderSummary)
  );
}

export function isCustomerOrderDetail(value: unknown): value is CustomerOrderDetail {
  return isCheckoutOrder(value);
}

export function parseOrderPage(value: string | string[] | undefined) {
  const candidate = Array.isArray(value) ? value[0] : value;
  if (!candidate || !/^[1-9][0-9]*$/.test(candidate)) return 1;
  const page = Number(candidate);
  return Number.isSafeInteger(page) ? page : 1;
}

