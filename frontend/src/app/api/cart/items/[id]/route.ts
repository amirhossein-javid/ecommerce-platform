import { cookies } from "next/headers";

import {
  removeCustomerCartItem,
  removeGuestCartItem,
  updateCustomerCartItem,
  updateGuestCartItem,
} from "@/lib/cart-api";
import {
  normalizeGuestCartToken,
  parseCartItemId,
  parseQuantityInput,
} from "@/lib/cart-contract";
import {
  authenticatedCartResponse,
  authenticatedCartRouteError,
  cartRouteError,
  privateJson,
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

type CartItemRouteProps = {
  params: Promise<{ id: string }>;
};

export async function PATCH(
  request: Request,
  { params }: CartItemRouteProps,
) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateJson({ error: "درخواست غیرمجاز است." }, 403);
  }

  if (!hasJsonContentType(request.headers)) {
    return privateJson({ error: "تعداد معتبر نیست." }, 400);
  }

  let payload: unknown;

  try {
    payload = await request.json();
  } catch {
    return privateJson({ error: "تعداد معتبر نیست." }, 400);
  }

  const input = parseQuantityInput(payload);
  const { id } = await params;
  const itemId = parseCartItemId(id);

  if (!itemId || !input) {
    return privateJson({ error: "سبد خرید، آیتم یا تعداد معتبر نیست." }, 400);
  }

  if (await hasAuthenticationCookies()) {
    try {
      const result = await withAuthenticatedSession((access) =>
        updateCustomerCartItem(access, itemId, input.quantity),
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
  if (!token) {
    return privateJson({ error: "سبد خرید، آیتم یا تعداد معتبر نیست." }, 400);
  }

  try {
    return privateJson(
      await updateGuestCartItem(token, itemId, input.quantity),
    );
  } catch (error) {
    return cartRouteError(error);
  }
}

export async function DELETE(
  request: Request,
  { params }: CartItemRouteProps,
) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateJson({ error: "درخواست غیرمجاز است." }, 403);
  }

  const { id } = await params;
  const itemId = parseCartItemId(id);

  if (!itemId) {
    return privateJson({ error: "سبد خرید یا آیتم معتبر نیست." }, 400);
  }

  if (await hasAuthenticationCookies()) {
    try {
      const result = await withAuthenticatedSession((access) =>
        removeCustomerCartItem(access, itemId),
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
  if (!token) {
    return privateJson({ error: "سبد خرید یا آیتم معتبر نیست." }, 400);
  }

  try {
    return privateJson(await removeGuestCartItem(token, itemId));
  } catch (error) {
    return cartRouteError(error);
  }
}
