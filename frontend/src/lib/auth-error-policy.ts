export function isAuthenticationFailure(error: unknown) {
  if (!error || typeof error !== "object" || !("status" in error)) return false;
  return error.status === 401 || error.status === 403;
}
