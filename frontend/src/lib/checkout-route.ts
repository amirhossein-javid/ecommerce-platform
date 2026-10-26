import "server-only";

import type { AuthTokens } from "@/lib/auth-contract";
import { clearAuthCookies, refreshFailureResponse, setAuthCookies } from "@/lib/auth-route";
import {
  AuthSessionError,
  AuthenticatedOperationError,
} from "@/lib/authenticated-request";
import { CheckoutApiError } from "@/lib/checkout-api";
import { classifyCheckoutFailure } from "@/lib/checkout-error-policy";
import { privateJson } from "@/lib/cart-route";

export function checkoutResponse(
  body: unknown,
  rotatedTokens?: AuthTokens,
  status = 200,
) {
  const response = privateJson(body, status);
  if (rotatedTokens) setAuthCookies(response, rotatedTokens);
  return response;
}

export function checkoutRouteError(caught: unknown) {
  const error =
    caught instanceof AuthenticatedOperationError
      ? caught.originalError
      : caught;
  const rotatedTokens =
    caught instanceof AuthenticatedOperationError
      ? caught.rotatedTokens
      : undefined;

  if (error instanceof AuthSessionError) {
    const response = privateJson(
      { error: "نشست شما منقضی شده است. دوباره وارد شوید.", code: "session_expired" },
      401,
    );
    clearAuthCookies(response);
    return response;
  }

  const refreshFailure = refreshFailureResponse(error);
  if (refreshFailure) return refreshFailure;

  const failure =
    error instanceof CheckoutApiError
      ? classifyCheckoutFailure(
          error.status,
          error.payload,
          error.transportFailed,
        )
      : "upstream";

  let response;
  switch (failure) {
    case "address-required":
      response = privateJson(
        { error: "آدرس انتخاب‌شده در دسترس نیست. آدرس دیگری انتخاب کنید.", code: failure },
        400,
      );
      break;
    case "cart-unavailable":
      response = privateJson(
        { error: "سبد خرید فعال و غیرخالی پیدا نشد.", code: failure },
        400,
      );
      break;
    case "product-unavailable":
      response = privateJson(
        { error: "یکی از کالاهای سبد دیگر قابل سفارش نیست. سبد را بررسی کنید.", code: failure },
        400,
      );
      break;
    case "insufficient-stock":
      response = privateJson(
        { error: "موجودی یکی از کالاها برای تعداد انتخاب‌شده کافی نیست.", code: failure },
        400,
      );
      break;
    case "validation":
      response = privateJson(
        { error: "اطلاعات ثبت سفارش معتبر نیست.", code: failure },
        400,
      );
      break;
    case "missing-profile":
      response = privateJson(
        { error: "این حساب، پروفایل مشتری فروشگاه ندارد.", code: failure },
        403,
      );
      break;
    case "rate-limited":
      response = privateJson(
        { error: "تعداد تلاش‌ها زیاد است. کمی بعد دوباره اقدام کنید.", code: failure },
        429,
      );
      if (error instanceof CheckoutApiError && error.retryAfter) {
        response.headers.set("Retry-After", error.retryAfter);
      }
      break;
    case "outcome-unknown":
      response = privateJson(
        {
          error: "پاسخ ثبت سفارش دریافت نشد و نتیجه مشخص نیست. برای جلوگیری از سفارش تکراری، دوباره ارسال نکنید و وضعیت سبد را بررسی کنید.",
          code: failure,
        },
        503,
      );
      break;
    default:
      response = privateJson(
        { error: "ارتباط با سرویس ثبت سفارش برقرار نشد. کمی بعد دوباره تلاش کنید.", code: "upstream" },
        503,
      );
  }

  if (rotatedTokens) setAuthCookies(response, rotatedTokens);
  return response;
}
