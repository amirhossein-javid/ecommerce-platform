import { cookies } from "next/headers";

import {
  CartApiError,
  fetchCustomerCart,
  fetchGuestCart,
} from "@/lib/cart-api";
import { EMPTY_CART, normalizeGuestCartToken } from "@/lib/cart-contract";
import {
  authenticatedCartResponse,
  authenticatedCartRouteError,
  cartRouteError,
  clearGuestCartCookie,
  privateJson,
} from "@/lib/cart-route";
import { GUEST_CART_COOKIE_NAME } from "@/lib/cart-security";
import {
  hasAuthenticationCookies,
  withAuthenticatedSession,
} from "@/lib/authenticated-request";

export async function GET() {
  if (await hasAuthenticationCookies()) {
    try {
      const result = await withAuthenticatedSession(fetchCustomerCart);
      return authenticatedCartResponse(result.value, result.rotatedTokens);
    } catch (error) {
      return authenticatedCartRouteError(error);
    }
  }

  const cookieStore = await cookies();
  const rawToken = cookieStore.get(GUEST_CART_COOKIE_NAME)?.value;
  const token = normalizeGuestCartToken(rawToken);

  if (rawToken && !token) {
    const response = privateJson(EMPTY_CART);
    clearGuestCartCookie(response);
    return response;
  }

  try {
    return privateJson(await fetchGuestCart(token));
  } catch (error) {
    if (token && error instanceof CartApiError && error.status === 404) {
      const response = privateJson(EMPTY_CART);
      clearGuestCartCookie(response);
      return response;
    }
    return cartRouteError(error);
  }
}
