export type CheckoutFailure =
  | "address-required"
  | "cart-unavailable"
  | "product-unavailable"
  | "insufficient-stock"
  | "validation"
  | "missing-profile"
  | "not-found"
  | "rate-limited"
  | "upstream"
  | "outcome-unknown";

function detailMessages(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return [];
  }
  const detail = (payload as Record<string, unknown>).detail;
  if (typeof detail === "string") return [detail];
  return Array.isArray(detail)
    ? detail.filter((item): item is string => typeof item === "string")
    : [];
}

export function classifyCheckoutFailure(
  status?: number,
  payload?: unknown,
  transportFailed = false,
): CheckoutFailure {
  if (transportFailed || (status !== undefined && status >= 500)) {
    return "outcome-unknown";
  }
  if (status === 429) return "rate-limited";
  if (status === 404) {
    return detailMessages(payload).includes("Customer profile not found.")
      ? "missing-profile"
      : "not-found";
  }
  if (status !== 400) return "upstream";

  const messages = detailMessages(payload);
  if (messages.includes("A usable shipping address is required.")) {
    return "address-required";
  }
  if (messages.includes("An active, non-empty cart is required.")) {
    return "cart-unavailable";
  }
  if (messages.includes("The cart contains an unavailable product.")) {
    return "product-unavailable";
  }
  if (messages.includes("The cart quantity exceeds available stock.")) {
    return "insufficient-stock";
  }
  return "validation";
}
