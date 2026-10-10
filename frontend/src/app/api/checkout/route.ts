import { checkoutCustomerCart } from "@/lib/checkout-api";
import { parseCheckoutInput } from "@/lib/checkout-contract";
import { checkoutResponse, checkoutRouteError } from "@/lib/checkout-route";
import { privateJson } from "@/lib/cart-route";
import { withAuthenticatedSession } from "@/lib/authenticated-request";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateJson({ error: "اطلاعات ثبت سفارش معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateJson({ error: "اطلاعات ثبت سفارش معتبر نیست." }, 400);
  }

  const input = parseCheckoutInput(payload);
  if (!input) {
    return privateJson({ error: "آدرس انتخاب‌شده معتبر نیست." }, 400);
  }

  try {
    const result = await withAuthenticatedSession((access) =>
      checkoutCustomerCart(access, input.addressId),
    );
    return checkoutResponse(result.value, result.rotatedTokens, 201);
  } catch (error) {
    return checkoutRouteError(error);
  }
}
