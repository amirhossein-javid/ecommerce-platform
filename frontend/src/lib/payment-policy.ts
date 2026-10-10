export type PaymentFailure =
  | "validation"
  | "missing-profile"
  | "not-found"
  | "not-payable"
  | "expired"
  | "rate-limited"
  | "gateway-unavailable"
  | "gateway-invalid"
  | "upstream";

function detail(payload: unknown) {
  return payload && typeof payload === "object" && !Array.isArray(payload) &&
    "detail" in payload && typeof payload.detail === "string"
    ? payload.detail
    : undefined;
}

export function classifyPaymentFailure(status?: number, payload?: unknown): PaymentFailure {
  const message = detail(payload);
  if (status === 400) return "validation";
  if (status === 404) {
    return message === "Customer profile not found." ? "missing-profile" : "not-found";
  }
  if (status === 409) {
    return message === "The order payment window has expired." ? "expired" : "not-payable";
  }
  if (status === 429) return "rate-limited";
  if (status === 502) return "gateway-invalid";
  if (status === 503) return "gateway-unavailable";
  return "upstream";
}

export function canRetryPayment(orderStatus: string, paymentStatus?: string) {
  return orderStatus === "PENDING_PAYMENT" && paymentStatus !== "SUCCESS";
}
