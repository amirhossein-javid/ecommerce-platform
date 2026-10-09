import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { AuthApiError, fetchCustomerProfile } from "@/lib/auth-api";
import { normalizeToken } from "@/lib/auth-contract";
import { ACCESS_COOKIE_NAME } from "@/lib/auth-security";

export const getCurrentCustomer = cache(async () => {
  const cookieStore = await cookies();
  const access = normalizeToken(cookieStore.get(ACCESS_COOKIE_NAME)?.value);
  if (!access) {
    return null;
  }

  try {
    return await fetchCustomerProfile(access);
  } catch (error) {
    if (error instanceof AuthApiError && (error.status === 401 || error.status === 403)) {
      return null;
    }
    return null;
  }
});
