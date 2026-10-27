import { cookies } from "next/headers";

import {
  AuthApiError,
  fetchCustomerProfile,
  loginCustomer,
  logoutCustomer,
} from "@/lib/auth-api";
import { CartApiError, mergeGuestCart } from "@/lib/cart-api";
import { normalizeGuestCartToken } from "@/lib/cart-contract";
import {
  classifyCartMergeFailure,
  type LoginCartMergeState,
  successfulCartMerge,
} from "@/lib/cart-merge-policy";
import { parseLoginInput } from "@/lib/auth-contract";
import {
  authRouteError,
  clearAuthCookies,
  privateAuthJson,
  setAuthCookies,
} from "@/lib/auth-route";
import {
  GUEST_CART_COOKIE_NAME,
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";
import { clearGuestCartCookie } from "@/lib/cart-route";
import { verifyStorefrontCustomer } from "@/lib/customer-login-policy";
import { trustedClientIp } from "@/lib/client-identity";

function profileVerificationError(error: unknown) {
  let response;
  if (error instanceof AuthApiError && error.status === 404) {
    response = privateAuthJson(
      { error: "این حساب، پروفایل مشتری فروشگاه ندارد." },
      403,
    );
  } else if (
    error instanceof AuthApiError &&
    (error.status === 401 || error.status === 403)
  ) {
    response = privateAuthJson(
      { error: "اعتبار ورود تأیید نشد. دوباره تلاش کنید." },
      401,
    );
  } else {
    response = privateAuthJson(
      { error: "بررسی حساب مشتری ممکن نشد. کمی بعد دوباره تلاش کنید." },
      503,
    );
  }
  clearAuthCookies(response);
  return response;
}

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateAuthJson({ error: "اطلاعات ورود معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateAuthJson({ error: "اطلاعات ورود معتبر نیست." }, 400);
  }

  const input = parseLoginInput(payload);
  if (!input) {
    return privateAuthJson({ error: "ایمیل و رمز عبور معتبر وارد کنید." }, 400);
  }

  try {
    const clientIp = trustedClientIp(request.headers);
    const tokens = await loginCustomer(input.email, input.password, clientIp);
    try {
      await verifyStorefrontCustomer(
        tokens,
        fetchCustomerProfile,
        (refresh) => logoutCustomer(refresh, clientIp),
      );
    } catch (error) {
      return profileVerificationError(error);
    }

    const cookieStore = await cookies();
    const rawGuestToken = cookieStore.get(GUEST_CART_COOKIE_NAME)?.value;
    const guestToken = normalizeGuestCartToken(rawGuestToken);
    let cartMerge: LoginCartMergeState = "none";
    let clearGuest = false;

    if (rawGuestToken) {
      if (!guestToken) {
        cartMerge = "unavailable";
        clearGuest = true;
      } else {
        try {
          await mergeGuestCart(tokens.access, guestToken);
          const decision = successfulCartMerge();
          cartMerge = decision.state;
          clearGuest = decision.clearGuestCookie;
        } catch (error) {
          const decision = classifyCartMergeFailure(
            error instanceof CartApiError ? error.status : undefined,
          );
          if (!decision.establishSession) {
            try {
              await logoutCustomer(tokens.refresh, clientIp);
            } catch {
              // Tokens are never exposed if best-effort revocation is unavailable.
            }
            const response = privateAuthJson(
              { error: "اتصال امن حساب و سبد خرید تأیید نشد. دوباره تلاش کنید." },
              401,
            );
            clearAuthCookies(response);
            return response;
          }
          cartMerge = decision.state;
          clearGuest = decision.clearGuestCookie;
        }
      }
    }

    const response = privateAuthJson({ authenticated: true, cartMerge });
    setAuthCookies(response, tokens);
    if (clearGuest) clearGuestCartCookie(response);
    return response;
  } catch (error) {
    return authRouteError(error, "login");
  }
}
