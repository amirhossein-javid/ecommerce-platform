import { cookies } from "next/headers";

import {
  removeGuestCartItem,
  updateGuestCartItem,
} from "@/lib/cart-api";
import {
  normalizeGuestCartToken,
  parseCartItemId,
  parseQuantityInput,
} from "@/lib/cart-contract";
import { cartRouteError, privateJson } from "@/lib/cart-route";
import {
  GUEST_CART_COOKIE_NAME,
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

type CartItemRouteProps = {
  params: Promise<{ id: string }>;
};

async function getRequestIdentity(params: CartItemRouteProps["params"]) {
  const { id } = await params;
  const itemId = parseCartItemId(id);
  const cookieStore = await cookies();
  const token = normalizeGuestCartToken(
    cookieStore.get(GUEST_CART_COOKIE_NAME)?.value,
  );

  return { itemId, token };
}

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
  const { itemId, token } = await getRequestIdentity(params);

  if (!itemId || !token || !input) {
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

  const { itemId, token } = await getRequestIdentity(params);

  if (!itemId || !token) {
    return privateJson({ error: "سبد خرید یا آیتم معتبر نیست." }, 400);
  }

  try {
    return privateJson(await removeGuestCartItem(token, itemId));
  } catch (error) {
    return cartRouteError(error);
  }
}
