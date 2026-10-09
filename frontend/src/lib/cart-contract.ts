const WHOLE_RIAL_PATTERN = /^\d+$/;
const UNICODE_SLUG_PATTERN = /^[\p{L}\p{M}\p{N}_-]+$/u;
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const MAX_CART_QUANTITY = 2_147_483_647;
export const MAX_PRODUCT_SLUG_LENGTH = 255;

export type CartProductImage = {
  id: number;
  image: string;
  alt_text: string;
  is_primary: boolean;
  position: number;
};

export type CartProduct = {
  slug: string;
  name: string;
  price: string;
  primary_image: CartProductImage | null;
};

export type CartItem = {
  id: number;
  product: CartProduct;
  quantity: number;
  line_total: string;
  is_available: boolean;
  availability_reason: "unavailable" | "insufficient_stock" | null;
};

export type Cart = {
  items: CartItem[];
  subtotal: string;
};

export const EMPTY_CART: Cart = { items: [], subtotal: "0" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isPositiveInteger(value: unknown): value is number {
  return (
    Number.isSafeInteger(value) &&
    Number(value) > 0
  );
}

function isCartProductImage(value: unknown): value is CartProductImage {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isPositiveInteger(value.id) &&
    typeof value.image === "string" &&
    typeof value.alt_text === "string" &&
    typeof value.is_primary === "boolean" &&
    Number.isSafeInteger(value.position) &&
    Number(value.position) >= 0
  );
}

function isCartProduct(value: unknown): value is CartProduct {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isValidProductSlug(value.slug) &&
    typeof value.name === "string" &&
    WHOLE_RIAL_PATTERN.test(String(value.price)) &&
    (value.primary_image === null || isCartProductImage(value.primary_image))
  );
}

function isCartItem(value: unknown): value is CartItem {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isPositiveInteger(value.id) &&
    isCartProduct(value.product) &&
    parseQuantity(value.quantity) !== null &&
    typeof value.line_total === "string" &&
    WHOLE_RIAL_PATTERN.test(value.line_total) &&
    typeof value.is_available === "boolean" &&
    (value.availability_reason === null ||
      value.availability_reason === "unavailable" ||
      value.availability_reason === "insufficient_stock")
  );
}

export function isCart(value: unknown): value is Cart {
  if (!isRecord(value)) {
    return false;
  }

  return (
    Array.isArray(value.items) &&
    value.items.every(isCartItem) &&
    typeof value.subtotal === "string" &&
    WHOLE_RIAL_PATTERN.test(value.subtotal)
  );
}

export function isValidProductSlug(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= MAX_PRODUCT_SLUG_LENGTH &&
    value.trim() === value &&
    UNICODE_SLUG_PATTERN.test(value)
  );
}

export function parseQuantity(value: unknown): number | null {
  return isPositiveInteger(value) && Number(value) <= MAX_CART_QUANTITY
    ? Number(value)
    : null;
}

export function parseAddCartInput(value: unknown) {
  if (!isRecord(value)) {
    return null;
  }

  const keys = Object.keys(value);
  const quantity = parseQuantity(value.quantity);

  if (
    keys.length !== 2 ||
    !keys.includes("productSlug") ||
    !keys.includes("quantity") ||
    !isValidProductSlug(value.productSlug) ||
    quantity === null
  ) {
    return null;
  }

  return { productSlug: value.productSlug, quantity };
}

export function parseQuantityInput(value: unknown) {
  if (!isRecord(value)) {
    return null;
  }

  const keys = Object.keys(value);
  const quantity = parseQuantity(value.quantity);

  return keys.length === 1 && keys[0] === "quantity" && quantity !== null
    ? { quantity }
    : null;
}

export function parseCartItemId(value: string): number | null {
  if (!/^\d+$/.test(value)) {
    return null;
  }

  const parsed = Number(value);
  return isPositiveInteger(parsed) ? parsed : null;
}

export function normalizeGuestCartToken(value: string | undefined) {
  return value && UUID_PATTERN.test(value) ? value.toLowerCase() : undefined;
}

export function getCartItemCount(cart: Cart) {
  return cart.items.reduce((total, item) => total + item.quantity, 0);
}
