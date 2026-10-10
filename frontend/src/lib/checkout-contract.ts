const WHOLE_RIAL_PATTERN = /^\d+$/;

export const ORDER_STATUSES = [
  "PENDING_PAYMENT",
  "PAID",
  "PROCESSING",
  "SHIPPED",
  "DELIVERED",
  "CANCELLED",
  "EXPIRED",
] as const;

export type OrderStatus = (typeof ORDER_STATUSES)[number];

export type CheckoutOrderItem = {
  id?: number;
  product_name: string;
  sku: string;
  unit_price: string;
  quantity: number;
  line_total: string;
};

export type CheckoutOrder = {
  id: number;
  status: OrderStatus;
  subtotal: string;
  discount_total: string;
  shipping_total: string;
  grand_total: string;
  shipping_title: string;
  shipping_recipient_first_name: string;
  shipping_recipient_last_name: string;
  shipping_recipient_phone_number: string;
  shipping_province: string;
  shipping_city: string;
  shipping_address: string;
  shipping_postal_code: string;
  items: CheckoutOrderItem[];
  created_at: string;
  payment_expires_at?: string | null;
  updated_at?: string;
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

export function isOrderStatus(value: unknown): value is OrderStatus {
  return (
    typeof value === "string" &&
    (ORDER_STATUSES as readonly string[]).includes(value)
  );
}

export function isCheckoutOrder(value: unknown): value is CheckoutOrder {
  if (!isRecord(value)) return false;

  return (
    isPositiveInteger(value.id) &&
    isOrderStatus(value.status) &&
    isMoney(value.subtotal) &&
    isMoney(value.discount_total) &&
    isMoney(value.shipping_total) &&
    isMoney(value.grand_total) &&
    typeof value.shipping_title === "string" &&
    typeof value.shipping_recipient_first_name === "string" &&
    typeof value.shipping_recipient_last_name === "string" &&
    typeof value.shipping_recipient_phone_number === "string" &&
    typeof value.shipping_province === "string" &&
    typeof value.shipping_city === "string" &&
    typeof value.shipping_address === "string" &&
    typeof value.shipping_postal_code === "string" &&
    Array.isArray(value.items) &&
    value.items.every(isOrderItem) &&
    isDateTime(value.created_at) &&
    (value.payment_expires_at === undefined ||
      value.payment_expires_at === null ||
      isDateTime(value.payment_expires_at)) &&
    (value.updated_at === undefined || isDateTime(value.updated_at))
  );
}

export function parseCheckoutInput(value: unknown) {
  if (!isRecord(value)) return null;
  const keys = Object.keys(value);
  if (keys.length !== 1 || keys[0] !== "addressId") return null;
  return isPositiveInteger(value.addressId)
    ? { addressId: Number(value.addressId) }
    : null;
}

export function parseOrderId(value: string) {
  if (!/^[1-9][0-9]*$/.test(value)) return null;
  const id = Number(value);
  return isPositiveInteger(id) ? id : null;
}
