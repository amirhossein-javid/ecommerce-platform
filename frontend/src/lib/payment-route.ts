import "server-only";

import type { AuthTokens } from "@/lib/auth-contract";
import { clearAuthCookies, refreshFailureResponse, setAuthCookies } from "@/lib/auth-route";
import {
  AuthSessionError,
  AuthenticatedOperationError,
} from "@/lib/authenticated-request";
import { privateJson } from "@/lib/cart-route";
import { PaymentApiError, PaymentHandoffError } from "@/lib/payment-api";
import { classifyPaymentFailure } from "@/lib/payment-policy";

export function paymentResponse(body: unknown, tokens?: AuthTokens, status = 200) {
  const response = privateJson(body, status);
  if (tokens) setAuthCookies(response, tokens);
  return response;
}

export function paymentRouteError(caught: unknown) {
  const error =
    caught instanceof AuthenticatedOperationError ? caught.originalError : caught;
  const tokens =
    caught instanceof AuthenticatedOperationError ? caught.rotatedTokens : undefined;

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

  let response;
  if (error instanceof PaymentHandoffError) {
    response = privateJson(
      { error: "نشانی انتقال به درگاه مورد اعتماد نیست. پرداخت آغاز نشد.", code: "unsafe_handoff" },
      502,
    );
  } else {
    const failure =
      error instanceof PaymentApiError
        ? classifyPaymentFailure(error.status, error.payload)
        : "upstream";
    const messages: Record<string, string> = {
      validation: "اطلاعات بازگشت از درگاه معتبر نیست.",
      "missing-profile": "این حساب، پروفایل مشتری فروشگاه ندارد.",
      "not-found": "سفارش یا تلاش پرداخت پیدا نشد.",
      "not-payable": "این سفارش در وضعیت قابل پرداخت نیست.",
      expired: "مهلت پرداخت سفارش به پایان رسیده است.",
      "rate-limited": "تعداد درخواست‌های پرداخت زیاد است. کمی بعد دوباره تلاش کنید.",
      "gateway-unavailable": "درگاه پرداخت موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.",
      "gateway-invalid": "پاسخ درگاه پرداخت معتبر نبود. وضعیت سفارش را بررسی کنید.",
      upstream: "ارتباط با سرویس پرداخت برقرار نشد. کمی بعد دوباره تلاش کنید.",
    };
    const statuses: Record<string, number> = {
      validation: 400,
      "missing-profile": 403,
      "not-found": 404,
      "not-payable": 409,
      expired: 409,
      "rate-limited": 429,
      "gateway-unavailable": 503,
      "gateway-invalid": 502,
      upstream: 503,
    };
    response = privateJson(
      { error: messages[failure], code: failure },
      statuses[failure],
    );
    if (failure === "rate-limited" && error instanceof PaymentApiError && error.retryAfter) {
      response.headers.set("Retry-After", error.retryAfter);
    }
  }

  if (tokens) setAuthCookies(response, tokens);
  return response;
}
