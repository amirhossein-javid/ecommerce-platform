import "server-only";

import { NextResponse } from "next/server";

import { AuthApiError } from "@/lib/auth-api";
import type { AuthTokens } from "@/lib/auth-contract";
import {
  ACCESS_COOKIE_NAME,
  getAuthCookieOptions,
  REFRESH_COOKIE_NAME,
} from "@/lib/auth-security";

const PRIVATE_HEADERS = {
  "Cache-Control": "private, no-store, max-age=0, must-revalidate",
};

export function privateAuthJson(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: PRIVATE_HEADERS });
}

export function setAuthCookies(response: NextResponse, tokens: AuthTokens) {
  const isProduction = process.env.NODE_ENV === "production";
  response.cookies.set(
    ACCESS_COOKIE_NAME,
    tokens.access,
    getAuthCookieOptions("access", isProduction),
  );
  response.cookies.set(
    REFRESH_COOKIE_NAME,
    tokens.refresh,
    getAuthCookieOptions("refresh", isProduction),
  );
}

export function clearAuthCookies(response: NextResponse) {
  const isProduction = process.env.NODE_ENV === "production";
  response.cookies.set(ACCESS_COOKIE_NAME, "", {
    ...getAuthCookieOptions("access", isProduction),
    maxAge: 0,
  });
  response.cookies.set(REFRESH_COOKIE_NAME, "", {
    ...getAuthCookieOptions("refresh", isProduction),
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

export function authRouteError(error: unknown, operation: "login" | "register") {
  if (!(error instanceof AuthApiError)) {
    return privateAuthJson({ error: "ارتباط با سرویس حساب کاربری برقرار نشد." }, 503);
  }

  if (error.status === 429) {
    const response = privateAuthJson(
      { error: "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید." },
      429,
    );
    if (error.retryAfter) {
      response.headers.set("Retry-After", error.retryAfter);
    }
    return response;
  }

  if (operation === "login" && (error.status === 400 || error.status === 401)) {
    return privateAuthJson(
      { error: "ایمیل یا رمز عبور صحیح نیست." },
      401,
    );
  }

  if (operation === "register" && error.status === 400) {
    const fieldErrors: Record<string, string> = {};
    if (hasField(error.payload, "email")) {
      fieldErrors.email = "این ایمیل قابل استفاده نیست یا قبلاً ثبت شده است.";
    }
    if (hasField(error.payload, "password")) {
      fieldErrors.password = "رمز عبور شرایط امنیتی لازم را ندارد.";
    }
    if (hasField(error.payload, "first_name")) {
      fieldErrors.first_name = "نام واردشده معتبر نیست.";
    }
    if (hasField(error.payload, "last_name")) {
      fieldErrors.last_name = "نام خانوادگی واردشده معتبر نیست.";
    }
    if (hasField(error.payload, "phone_number")) {
      fieldErrors.phone_number = "شماره تلفن را با قالب بین‌المللی وارد کنید.";
    }
    return privateAuthJson(
      {
        error: "اطلاعات ثبت‌نام نیاز به اصلاح دارد.",
        fieldErrors,
      },
      400,
    );
  }

  return privateAuthJson({ error: "ارتباط با سرویس حساب کاربری برقرار نشد." }, 503);
}
