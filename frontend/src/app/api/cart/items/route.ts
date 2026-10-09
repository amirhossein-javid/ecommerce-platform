import { cookies } from "next/headers";

import { addGuestCartItem, CartApiError } from "@/lib/cart-api";
import {
  normalizeGuestCartToken,
  parseAddCartInput,
} from "@/lib/cart-contract";
import {
  cartRouteError,
  privateJson,
  setGuestCartCookie,
} from "@/lib/cart-route";
import {
  GUEST_CART_COOKIE_NAME,
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

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
