import { loginCustomer, logoutCustomer } from "@/lib/auth-api";
import { parseLoginInput } from "@/lib/auth-contract";
import { authRouteError } from "@/lib/auth-route";
import {
  privateManagementJson,
  setManagementCookies,
} from "@/lib/management-auth-route";
import {
  fetchManagedReviews,
  ManagementReviewApiError,
} from "@/lib/management-review-api";
import {
  fetchManagementSummary,
  ManagementOrderApiError,
} from "@/lib/management-order-api";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";
import { trustedClientIp } from "@/lib/client-identity";

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateManagementJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateManagementJson({ error: "اطلاعات ورود معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateManagementJson({ error: "اطلاعات ورود معتبر نیست." }, 400);
  }
  const input = parseLoginInput(payload);
  if (!input) {
    return privateManagementJson({ error: "ایمیل و رمز عبور معتبر وارد کنید." }, 400);
  }

  try {
    const clientIp = trustedClientIp(request.headers);
    const tokens = await loginCustomer(input.email, input.password, clientIp);
    let accessGranted = false;
    let accessCheckUnavailable = false;
    try {
      await fetchManagementSummary(tokens.access);
      accessGranted = true;
    } catch (error) {
      accessCheckUnavailable = !(error instanceof ManagementOrderApiError && error.status === 403);
    }
    if (!accessGranted) {
      try {
        await fetchManagedReviews(tokens.access, "?page_size=1");
        accessGranted = true;
      } catch (error) {
        accessCheckUnavailable ||= !(error instanceof ManagementReviewApiError && error.status === 403);
      }
    }
    if (!accessGranted) {
      try {
        await logoutCustomer(tokens.refresh, clientIp);
      } catch {
        // The unexposed refresh token is revoked on a best-effort basis.
      }
      if (!accessCheckUnavailable) {
        return privateManagementJson(
          { error: "این حساب مجوز ورود به داشبورد مدیریت را ندارد." },
          403,
        );
      }
      return privateManagementJson(
        { error: "تأیید دسترسی مدیریت ممکن نشد." },
        503,
      );
    }
    const response = privateManagementJson({ authenticated: true });
    setManagementCookies(response, tokens);
    return response;
  } catch (error) {
    const response = authRouteError(error, "login");
    const retryAfter = response.headers.get("Retry-After");
    if (
      retryAfter &&
      !/^\d+$/.test(retryAfter) &&
      (Number.isNaN(Date.parse(retryAfter)) ||
        new Date(retryAfter).toUTCString() !== retryAfter)
    ) {
      response.headers.delete("Retry-After");
    }
    return response;
  }
}
