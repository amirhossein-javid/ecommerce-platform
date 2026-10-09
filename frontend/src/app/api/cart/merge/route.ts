import { cookies } from "next/headers";

import { CartApiError, mergeGuestCart } from "@/lib/cart-api";
import { normalizeGuestCartToken } from "@/lib/cart-contract";
import {
  authenticatedCartResponse,
  authenticatedCartRouteError,
  clearGuestCartCookie,
  privateJson,
} from "@/lib/cart-route";
import {
  GUEST_CART_COOKIE_NAME,
  isTrustedMutationRequest,
} from "@/lib/cart-security";
import { setAuthCookies } from "@/lib/auth-route";
import {
  AuthenticatedOperationError,
  withAuthenticatedSession,
} from "@/lib/authenticated-request";

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateJson({ error: "درخواست غیرمجاز است." }, 403);
  }

  const cookieStore = await cookies();
  const rawToken = cookieStore.get(GUEST_CART_COOKIE_NAME)?.value;
  const guestToken = normalizeGuestCartToken(rawToken);
  if (!guestToken) {
    const response = privateJson(
      { error: "سبد مهمان دیگری برای ادغام در دسترس نیست." },
      409,
    );
    if (rawToken) clearGuestCartCookie(response);
    return response;
  }

  try {
    const result = await withAuthenticatedSession((access) =>
      mergeGuestCart(access, guestToken),
    );
    const response = authenticatedCartResponse(
      result.value,
      result.rotatedTokens,
    );
    clearGuestCartCookie(response);
    return response;
  } catch (caught) {
    const error =
      caught instanceof AuthenticatedOperationError
        ? caught.originalError
        : caught;
    if (error instanceof CartApiError && error.status === 404) {
      const response = privateJson(
        {
          error:
            "سبد مهمان قبلاً مصرف شده یا دیگر در دسترس نیست؛ سبد فعلی حساب را بررسی کنید.",
        },
        409,
      );
      if (caught instanceof AuthenticatedOperationError) {
        setAuthCookies(response, caught.rotatedTokens);
      }
      clearGuestCartCookie(response);
      return response;
    }
    return authenticatedCartRouteError(caught);
  }
}
