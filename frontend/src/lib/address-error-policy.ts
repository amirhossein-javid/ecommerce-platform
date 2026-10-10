export type AddressApiFailure =
  | "validation"
  | "missing-profile"
  | "not-found"
  | "rate-limited"
  | "upstream";

function detail(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return undefined;
  return "detail" in payload && typeof payload.detail === "string"
    ? payload.detail
    : undefined;
}

export function classifyAddressApiFailure(
  status?: number,
  payload?: unknown,
): AddressApiFailure {
  if (status === 400) return "validation";
  if (status === 404) {
    return detail(payload) === "Customer profile not found."
      ? "missing-profile"
      : "not-found";
  }
  if (status === 429) return "rate-limited";
  return "upstream";
}
