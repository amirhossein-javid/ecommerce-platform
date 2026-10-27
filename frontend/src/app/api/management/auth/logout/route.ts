import { cookies } from "next/headers";

import { logoutCustomer } from "@/lib/auth-api";
import { normalizeToken } from "@/lib/auth-contract";
import {
  clearManagementCookies,
  privateManagementJson,
} from "@/lib/management-auth-route";
import { MANAGEMENT_REFRESH_COOKIE_NAME } from "@/lib/management-auth-security";
import { isTrustedMutationRequest } from "@/lib/cart-security";
import { trustedClientIp } from "@/lib/client-identity";

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateManagementJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  const cookieStore = await cookies();
  const refresh = normalizeToken(
    cookieStore.get(MANAGEMENT_REFRESH_COOKIE_NAME)?.value,
  );
  if (refresh) {
    try {
      await logoutCustomer(refresh, trustedClientIp(request.headers));
    } catch {
      // Local session removal must still succeed if revocation is unavailable.
    }
  }
  const response = privateManagementJson({ authenticated: false });
  clearManagementCookies(response);
  return response;
}
