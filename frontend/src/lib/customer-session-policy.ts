export type CustomerProfileFailureState =
  | "missing-profile"
  | "invalid"
  | "upstream-error";

export function classifyCustomerProfileFailure(
  status?: number,
): CustomerProfileFailureState {
  if (status === 404) return "missing-profile";
  if (status === 401 || status === 403) return "invalid";
  return "upstream-error";
}
