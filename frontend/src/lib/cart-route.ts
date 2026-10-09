import "server-only";

import { NextResponse } from "next/server";

import { CartApiError } from "@/lib/cart-api";
import {
  getGuestCartCookieOptions,
  GUEST_CART_COOKIE_NAME,
} from "@/lib/cart-security";

const PRIVATE_HEADERS = {
  "Cache-Control": "private, no-store, max-age=0, must-revalidate",
};

export function privateJson(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: PRIVATE_HEADERS });
}

export function setGuestCartCookie(response: NextResponse, token: string) {
  response.cookies.set(
    GUEST_CART_COOKIE_NAME,
    token,
    getGuestCartCookieOptions(process.env.NODE_ENV === "production"),
  );
}

export function clearGuestCartCookie(response: NextResponse) {
  response.cookies.set(GUEST_CART_COOKIE_NAME, "", {
    ...getGuestCartCookieOptions(process.env.NODE_ENV === "production"),
    maxAge: 0,
  });
}

function hasField(payload: unknown, field: string) {
  return (
    payload !== null &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    field in payload
  );
}

export function cartRouteError(error: unknown) {
  if (!(error instanceof CartApiError)) {
    return privateJson(
      { error: "ارتباط با سرویس سبد خرید برقرار نشد." },
      503,
    );
  }

  if (error.status === 400) {
    const message = hasField(error.payload, "quantity")
      ? "تعداد انتخاب‌شده معتبر نیست یا از موجودی فعلی بیشتر است."
      : hasField(error.payload, "product_slug")
        ? "این محصول در حال حاضر قابل افزودن به سبد خرید نیست."
        : "درخواست سبد خرید معتبر نیست.";
    return privateJson({ error: message }, 400);
  }

  if (error.status === 404) {
    return privateJson(
      { error: "سبد خرید یا محصول مورد نظر پیدا نشد. صفحه را تازه کنید." },
      404,
    );
  }

  if (error.status === 429) {
    const response = privateJson(
      { error: "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید." },
      429,
    );
    if (error.retryAfter) {
      response.headers.set("Retry-After", error.retryAfter);
    }
    return response;
  }

  return privateJson(
    { error: "ارتباط با سرویس سبد خرید برقرار نشد." },
    503,
  );
}
