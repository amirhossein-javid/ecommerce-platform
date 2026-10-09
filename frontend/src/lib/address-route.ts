import "server-only";

import { AuthApiError } from "@/lib/auth-api";
import type { AuthTokens } from "@/lib/auth-contract";
import { classifyAddressApiFailure } from "@/lib/address-error-policy";
import { clearAuthCookies, privateAuthJson, setAuthCookies } from "@/lib/auth-route";
import {
  AuthSessionError,
  AuthenticatedOperationError,
} from "@/lib/authenticated-request";

const FIELD_MESSAGES: Record<string, string> = {
  title: "عنوان آدرس معتبر نیست.",
  recipient_first_name: "نام گیرنده معتبر نیست.",
  recipient_last_name: "نام خانوادگی گیرنده معتبر نیست.",
  recipient_phone_number: "شماره تماس را با قالب بین‌المللی وارد کنید.",
  province: "استان معتبر نیست.",
  city: "شهر معتبر نیست.",
  address: "نشانی کامل معتبر نیست.",
  postal_code: "کد پستی باید دقیقاً ۱۰ رقم انگلیسی باشد.",
};

function unwrapAddressError(error: unknown) {
  return error instanceof AuthenticatedOperationError
    ? { error: error.originalError, tokens: error.rotatedTokens }
    : { error, tokens: undefined };
}

export function addressResponse(
  body: unknown,
  rotatedTokens?: AuthTokens,
  status = 200,
) {
  const response = privateAuthJson(body, status);
  if (rotatedTokens) setAuthCookies(response, rotatedTokens);
  return response;
}

export function addressRouteError(caught: unknown) {
  const { error, tokens } = unwrapAddressError(caught);

  if (error instanceof AuthSessionError) {
    const response = privateAuthJson(
      { error: "نشست شما منقضی شده است. دوباره وارد شوید." },
      401,
    );
    clearAuthCookies(response);
    return response;
  }

  let response;
  const failure =
    error instanceof AuthApiError
      ? classifyAddressApiFailure(error.status, error.payload)
      : "upstream";
  if (error instanceof AuthApiError && failure === "validation") {
    const fieldErrors: Record<string, string> = {};
    if (error.payload && typeof error.payload === "object" && !Array.isArray(error.payload)) {
      for (const [field, message] of Object.entries(FIELD_MESSAGES)) {
        if (field in error.payload) fieldErrors[field] = message;
      }
    }
    response = privateAuthJson(
      { error: "اطلاعات آدرس نیاز به اصلاح دارد.", fieldErrors },
      400,
    );
  } else if (failure === "missing-profile") {
    response = privateAuthJson(
      {
        error: "این حساب، پروفایل مشتری فروشگاه ندارد.",
        accountState: "missing_profile",
      },
      403,
    );
  } else if (failure === "not-found") {
    response = privateAuthJson(
      { error: "آدرس پیدا نشد یا به این حساب تعلق ندارد." },
      404,
    );
  } else if (error instanceof AuthApiError && failure === "rate-limited") {
    response = privateAuthJson(
      { error: "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید." },
      429,
    );
    if (error.retryAfter) response.headers.set("Retry-After", error.retryAfter);
  } else {
    response = privateAuthJson(
      { error: "ارتباط با سرویس آدرس‌ها برقرار نشد. کمی بعد دوباره تلاش کنید." },
      503,
    );
  }

  if (tokens) setAuthCookies(response, tokens);
  return response;
}
