import { isOrderStatus, type OrderStatus } from "./checkout-contract.ts";

const MONEY = /^\d+$/;

export type RefundStatus = "NOT_REQUIRED" | "REQUIRED" | "RESOLVED";

export type ManagementSummary = {
  order_count: number;
  successful_revenue: string;
  pending_fulfillment_count: number;
  low_stock_product_count: number;
  low_stock_threshold: number;
};

export type ManagementOrderSummary = {
  id: number;
  status: OrderStatus;
  refund_status: RefundStatus;
  customer_display_name: string;
  item_count: number;
  grand_total: string;
  created_at: string;
  updated_at: string;
};

export type ManagementOrderPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ManagementOrderSummary[];
};

export type ManagementOrderDetail = ManagementOrderSummary & {
  customer_email: string;
  subtotal: string;
  discount_total: string;
  shipping_total: string;
  shipping_title: string;
  shipping_recipient_first_name: string;
  shipping_recipient_last_name: string;
  shipping_recipient_phone_number: string;
  shipping_province: string;
  shipping_city: string;
  shipping_address: string;
  shipping_postal_code: string;
  paid_at: string | null;
  processing_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  refund_resolved_at: string | null;
  items: Array<{
    id: number;
    product_name: string;
    sku: string;
    unit_price: string;
    quantity: number;
    line_total: string;
  }>;
  shipment: null | {
    carrier: string;
    tracking_number: string;
    created_at: string;
    updated_at: string;
  };
  status_history: Array<{
    from_status: OrderStatus;
    to_status: OrderStatus;
    actor_type: "CUSTOMER" | "OPERATOR" | "SYSTEM";
    actor_display_name: string;
    created_at: string;
  }>;
};

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function integer(value: unknown, positive = false) {
  return Number.isSafeInteger(value) && Number(value) >= (positive ? 1 : 0);
}

function date(value: unknown) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function nullableDate(value: unknown) {
  return value === null || date(value);
}

function money(value: unknown): value is string {
  return typeof value === "string" && MONEY.test(value);
}

function refund(value: unknown): value is RefundStatus {
  return value === "NOT_REQUIRED" || value === "REQUIRED" || value === "RESOLVED";
}

export function isManagementSummary(value: unknown): value is ManagementSummary {
  return record(value) && integer(value.order_count) && money(value.successful_revenue) &&
    integer(value.pending_fulfillment_count) && integer(value.low_stock_product_count) &&
    integer(value.low_stock_threshold);
}

export function isManagementOrderSummary(value: unknown): value is ManagementOrderSummary {
  return record(value) && integer(value.id, true) && isOrderStatus(value.status) &&
    refund(value.refund_status) && typeof value.customer_display_name === "string" &&
    integer(value.item_count) && money(value.grand_total) && date(value.created_at) && date(value.updated_at);
}

export function isManagementOrderPage(value: unknown): value is ManagementOrderPage {
  return record(value) && integer(value.count) &&
    (value.next === null || typeof value.next === "string") &&
    (value.previous === null || typeof value.previous === "string") &&
    Array.isArray(value.results) && value.results.every(isManagementOrderSummary);
}

export function isManagementOrderDetail(value: unknown): value is ManagementOrderDetail {
  if (!isManagementOrderSummary(value) || !record(value)) return false;
  const raw: Record<string, unknown> = value;
  const shipment = raw.shipment;
  return typeof raw.customer_email === "string" && money(raw.subtotal) &&
    money(raw.discount_total) && money(raw.shipping_total) &&
    ["shipping_title", "shipping_recipient_first_name", "shipping_recipient_last_name", "shipping_recipient_phone_number", "shipping_province", "shipping_city", "shipping_address", "shipping_postal_code"].every((key) => typeof raw[key] === "string") &&
    ["paid_at", "processing_at", "shipped_at", "delivered_at", "cancelled_at", "refund_resolved_at"].every((key) => nullableDate(raw[key])) &&
    Array.isArray(raw.items) && raw.items.every((item: unknown) => record(item) && integer(item.id, true) && typeof item.product_name === "string" && typeof item.sku === "string" && money(item.unit_price) && integer(item.quantity, true) && money(item.line_total)) &&
    (shipment === null || (record(shipment) && typeof shipment.carrier === "string" && typeof shipment.tracking_number === "string" && date(shipment.created_at) && date(shipment.updated_at))) &&
    Array.isArray(raw.status_history) && raw.status_history.every((entry: unknown) => record(entry) && isOrderStatus(entry.from_status) && isOrderStatus(entry.to_status) && ["CUSTOMER", "OPERATOR", "SYSTEM"].includes(String(entry.actor_type)) && typeof entry.actor_display_name === "string" && date(entry.created_at));
}

export function parseTransition(value: unknown) {
  if (!record(value) || Object.keys(value).length !== 1) return null;
  const allowed = ["PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"] as const;
  return allowed.includes(value.status as (typeof allowed)[number])
    ? { status: value.status as (typeof allowed)[number] }
    : null;
}

export function parseShipment(value: unknown) {
  if (!record(value) || Object.keys(value).length !== 2) return null;
  if (typeof value.carrier !== "string" || typeof value.tracking_number !== "string") return null;
  const carrier = value.carrier.trim();
  const tracking_number = value.tracking_number.trim();
  return carrier && carrier.length <= 100 && tracking_number && tracking_number.length <= 255
    ? { carrier, tracking_number }
    : null;
}
