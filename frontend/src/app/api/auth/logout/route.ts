import { cookies } from "next/headers";

import { logoutCustomer } from "@/lib/auth-api";
import { normalizeToken } from "@/lib/auth-contract";
import { clearAuthCookies, privateAuthJson } from "@/lib/auth-route";
import { REFRESH_COOKIE_NAME } from "@/lib/auth-security";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";
import { trustedClientIp } from "@/lib/client-identity";

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateAuthJson({ error: "درخواست خروج معتبر نیست." }, 400);
  }

  const cookieStore = await cookies();
  const refresh = normalizeToken(cookieStore.get(REFRESH_COOKIE_NAME)?.value);

  if (refresh) {
    try {
      await logoutCustomer(refresh, trustedClientIp(request.headers));
    } catch {
      // Local credentials are always cleared, including stale/invalid remote tokens.
    }
  }

  const response = privateAuthJson({ authenticated: false });
  clearAuthCookies(response);
  return response;
}
