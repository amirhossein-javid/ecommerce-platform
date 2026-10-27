import { AuthApiError, fetchCustomerProfile } from "@/lib/auth-api";
import { clearAuthCookies, privateAuthJson, refreshFailureResponse, setAuthCookies } from "@/lib/auth-route";
import {
  AuthenticatedOperationError,
  AuthSessionError,
  hasAuthenticationCookies,
  withAuthenticatedSession,
} from "@/lib/authenticated-request";

export async function GET() {
  if (!await hasAuthenticationCookies()) {
    return privateAuthJson({ authenticated: false, customer: null });
  }
  try {
    const result = await withAuthenticatedSession(fetchCustomerProfile);
    const response = privateAuthJson({ authenticated: true, customer: result.value });
    if (result.rotatedTokens) setAuthCookies(response, result.rotatedTokens);
    return response;
  } catch (caught) {
    const error = caught instanceof AuthenticatedOperationError ? caught.originalError : caught;
    const tokens = caught instanceof AuthenticatedOperationError ? caught.rotatedTokens : undefined;
    if (error instanceof AuthSessionError) {
      const response = privateAuthJson(
        { authenticated: false, customer: null, error: "نشست شما منقضی شده است." },
        401,
      );
      clearAuthCookies(response);
      return response;
    }
    const refreshFailure = refreshFailureResponse(error);
    if (refreshFailure) return refreshFailure;
    const response = error instanceof AuthApiError && error.status === 404
      ? privateAuthJson({
          authenticated: true,
          customer: null,
          accountState: "missing_profile",
          error: "این حساب، پروفایل مشتری فروشگاه ندارد.",
        }, 403)
      : privateAuthJson({ error: "بررسی وضعیت حساب ممکن نشد." }, 503);
    if (tokens) setAuthCookies(response, tokens);
    return response;
  }
}
