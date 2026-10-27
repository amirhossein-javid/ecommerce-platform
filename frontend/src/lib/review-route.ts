import "server-only";

import type { AuthTokens } from "@/lib/auth-contract";
import { clearAuthCookies, refreshFailureResponse, setAuthCookies } from "@/lib/auth-route";
import {
  AuthSessionError,
  AuthenticatedOperationError,
} from "@/lib/authenticated-request";
import { privateJson } from "@/lib/cart-route";
import { ReviewApiError } from "@/lib/review-api";

export function reviewResponse(
  body: unknown,
  rotatedTokens?: AuthTokens,
  status = 200,
) {
  const response = privateJson(body, status);
  if (rotatedTokens) setAuthCookies(response, rotatedTokens);
  return response;
}

function unwrapError(caught: unknown) {
  return caught instanceof AuthenticatedOperationError
    ? { error: caught.originalError, tokens: caught.rotatedTokens }
    : { error: caught, tokens: undefined };
}

export function reviewRouteError(caught: unknown, operation: "get" | "create" | "delete") {
  const { error, tokens } = unwrapError(caught);
  if (error instanceof AuthSessionError) {
    const response = privateJson(
      { error: "نشست شما منقضی شده است. دوباره وارد شوید." },
      401,
    );
    clearAuthCookies(response);
    return response;
  }

  const refreshFailure = refreshFailureResponse(error);
  if (refreshFailure) return refreshFailure;

  let response;
  if (error instanceof ReviewApiError && error.status === 404 && operation === "get") {
    response = reviewResponse({ review: null });
  } else if (error instanceof ReviewApiError && error.status === 400) {
    const payload = error.payload;
    const fieldErrors: Record<string, string> = {};
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      if ("rating" in payload) fieldErrors.rating = "امتیاز باید عددی بین ۱ تا ۵ باشد.";
      if ("comment" in payload) fieldErrors.comment = "متن نظر نمی‌تواند خالی باشد.";
    }
    response = reviewResponse(
      { error: "نظر نیاز به اصلاح دارد.", fieldErrors },
      undefined,
      400,
    );
  } else if (error instanceof ReviewApiError && error.status === 409) {
    response = reviewResponse(
      { error: "برای این محصول قبلاً نظر ثبت کرده‌اید." },
      undefined,
      409,
    );
  } else if (error instanceof ReviewApiError && error.status === 429) {
    response = reviewResponse(
      { error: "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید." },
      undefined,
      429,
    );
    if (error.retryAfter) response.headers.set("Retry-After", error.retryAfter);
  } else if (error instanceof ReviewApiError && error.status === 404) {
    response = reviewResponse(
      { error: "محصول یا پروفایل مشتری در دسترس نیست." },
      undefined,
      404,
    );
  } else {
    response = reviewResponse(
      { error: "ارتباط با سرویس نظرها برقرار نشد. کمی بعد دوباره تلاش کنید." },
      undefined,
      503,
    );
  }

  if (tokens) setAuthCookies(response, tokens);
  return response;
}
