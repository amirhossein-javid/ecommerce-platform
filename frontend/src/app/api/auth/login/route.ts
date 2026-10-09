import {
  AuthApiError,
  fetchCustomerProfile,
  loginCustomer,
  logoutCustomer,
} from "@/lib/auth-api";
import { parseLoginInput } from "@/lib/auth-contract";
import {
  authRouteError,
  clearAuthCookies,
  privateAuthJson,
  setAuthCookies,
} from "@/lib/auth-route";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";
import { verifyStorefrontCustomer } from "@/lib/customer-login-policy";

function profileVerificationError(error: unknown) {
  let response;
  if (error instanceof AuthApiError && error.status === 404) {
    response = privateAuthJson(
      { error: "این حساب، پروفایل مشتری فروشگاه ندارد." },
      403,
    );
  } else if (
    error instanceof AuthApiError &&
    (error.status === 401 || error.status === 403)
  ) {
    response = privateAuthJson(
      { error: "اعتبار ورود تأیید نشد. دوباره تلاش کنید." },
      401,
    );
  } else {
    response = privateAuthJson(
      { error: "بررسی حساب مشتری ممکن نشد. کمی بعد دوباره تلاش کنید." },
      503,
    );
  }
  clearAuthCookies(response);
  return response;
}

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateAuthJson({ error: "اطلاعات ورود معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateAuthJson({ error: "اطلاعات ورود معتبر نیست." }, 400);
  }

  const input = parseLoginInput(payload);
  if (!input) {
    return privateAuthJson({ error: "ایمیل و رمز عبور معتبر وارد کنید." }, 400);
  }

  try {
    const tokens = await loginCustomer(input.email, input.password);
    try {
      await verifyStorefrontCustomer(
        tokens,
        fetchCustomerProfile,
        logoutCustomer,
      );
    } catch (error) {
      return profileVerificationError(error);
    }
    const response = privateAuthJson({ authenticated: true });
    setAuthCookies(response, tokens);
    return response;
  } catch (error) {
    return authRouteError(error, "login");
  }
}
