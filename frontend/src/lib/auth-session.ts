import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { AuthApiError, fetchCustomerProfile } from "@/lib/auth-api";
import { type CustomerProfile, normalizeToken } from "@/lib/auth-contract";
import { ACCESS_COOKIE_NAME } from "@/lib/auth-security";
import { classifyCustomerProfileFailure } from "@/lib/customer-session-policy";

export type CustomerSession =
  | { state: "guest" }
  | { state: "customer"; customer: CustomerProfile }
  | { state: "missing-profile" }
  | { state: "invalid" }
  | { state: "upstream-error" };

export const getCustomerSession = cache(async (): Promise<CustomerSession> => {
  const cookieStore = await cookies();
  const access = normalizeToken(cookieStore.get(ACCESS_COOKIE_NAME)?.value);
  if (!access) {
    return { state: "guest" };
  }

  try {
    return { state: "customer", customer: await fetchCustomerProfile(access) };
  } catch (error) {
    return {
      state: classifyCustomerProfileFailure(
        error instanceof AuthApiError ? error.status : undefined,
      ),
    };
  }
});

export const getCurrentCustomer = cache(async () => {
  const session = await getCustomerSession();
  return session.state === "customer" ? session.customer : null;
});
