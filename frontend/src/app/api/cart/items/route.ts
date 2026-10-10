import { cookies } from "next/headers";

import {
  addCustomerCartItem,
  addGuestCartItem,
  CartApiError,
} from "@/lib/cart-api";
import {
  normalizeGuestCartToken,
  parseAddCartInput,
} from "@/lib/cart-contract";
import {
  authenticatedCartResponse,
  authenticatedCartRouteError,
  cartRouteError,
  privateJson,
  setGuestCartCookie,
} from "@/lib/cart-route";
import {
  GUEST_CART_COOKIE_NAME,
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";
import {
  hasAuthenticationCookies,
  withAuthenticatedSession,
} from "@/lib/authenticated-request";

async function parseRequestBody(request: Request) {
  if (!hasJsonContentType(request.headers)) {
    return null;
  }

  let payload: unknown;

  try {
    payload = await request.json();
  } catch {
    return null;
  }

  return parseAddCartInput(payload);
}

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateJson({ error: "درخواست غیرمجاز است." }, 403);
  }

  const input = await parseRequestBody(request);

  if (!input) {
    return privateJson({ error: "اطلاعات محصول یا تعداد معتبر نیست." }, 400);
  }

  if (await hasAuthenticationCookies()) {
    try {
      const result = await withAuthenticatedSession((access) =>
        addCustomerCartItem(access, input.productSlug, input.quantity),
      );
      return authenticatedCartResponse(result.value, result.rotatedTokens);
    } catch (error) {
      return authenticatedCartRouteError(error);
    }
  }

  const cookieStore = await cookies();
  const token = normalizeGuestCartToken(
    cookieStore.get(GUEST_CART_COOKIE_NAME)?.value,
  );

  try {
    let result;

    try {
      result = await addGuestCartItem(
        token,
        input.productSlug,
        input.quantity,
      );
    } catch (error) {
      if (!(token && error instanceof CartApiError && error.status === 404)) {
        throw error;
      }

      result = await addGuestCartItem(
        undefined,
        input.productSlug,
        input.quantity,
      );
    }

    const response = privateJson(result.cart);
    setGuestCartCookie(response, result.token);
    return response;
  } catch (error) {
    return cartRouteError(error);
  }
}
