import "server-only";

import {
  clearManagementCookies,
  privateManagementJson,
  setManagementCookies,
} from "@/lib/management-auth-route";
import {
  ManagementOperationError,
  ManagementSessionError,
} from "@/lib/management-authenticated-request";
import { ManagementReviewApiError } from "@/lib/management-review-api";

export function managementResultResponse<T>(result: {
  value: T;
  rotatedTokens?: Parameters<typeof setManagementCookies>[1];
}) {
  const response = privateManagementJson(result.value);
  if (result.rotatedTokens) setManagementCookies(response, result.rotatedTokens);
  return response;
}

export function managementRouteError(error: unknown) {
  const tokens =
    error instanceof ManagementOperationError ? error.rotatedTokens : undefined;
  const original =
    error instanceof ManagementOperationError ? error.originalError : error;

  if (original instanceof ManagementSessionError) {
    const response = privateManagementJson(
      { error: "نشست مدیریت منقضی شده است. دوباره وارد شوید." },
      401,
    );
    clearManagementCookies(response);
    return response;
  }

  let response;
  if (original instanceof ManagementReviewApiError && original.status === 403) {
    response = privateManagementJson(
      { error: "مجوز لازم برای این عملیات را ندارید." },
      403,
    );
  } else if (
    original instanceof ManagementReviewApiError &&
    original.status === 400
  ) {
    response = privateManagementJson(
      { error: "اطلاعات درخواست معتبر نیست." },
      400,
    );
  } else if (
    original instanceof ManagementReviewApiError &&
    original.status === 404
  ) {
    response = privateManagementJson({ error: "نظر یا پاسخ پیدا نشد." }, 404);
  } else if (
    original instanceof ManagementReviewApiError &&
    original.status === 409
  ) {
    response = privateManagementJson(
      { error: "وضعیت نظر یا پاسخ هم‌زمان تغییر کرده است؛ فهرست را تازه کنید." },
      409,
    );
  } else {
    response = privateManagementJson(
      { error: "ارتباط با سرویس مدیریت برقرار نشد." },
      503,
    );
  }
  if (tokens) setManagementCookies(response, tokens);
  return response;
}
