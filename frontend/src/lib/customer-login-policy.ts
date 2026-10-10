import type { AuthTokens, CustomerProfile } from "./auth-contract.ts";

export async function verifyStorefrontCustomer(
  tokens: AuthTokens,
  verifyProfile: (access: string) => Promise<CustomerProfile>,
  revokeRefresh: (refresh: string) => Promise<void>,
) {
  try {
    return await verifyProfile(tokens.access);
  } catch (error) {
    try {
      await revokeRefresh(tokens.refresh);
    } catch {
      // The browser never receives the tokens even if best-effort cleanup fails.
    }
    throw error;
  }
}
