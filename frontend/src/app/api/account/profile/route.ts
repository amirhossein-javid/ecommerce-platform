import {
  AuthApiError,
  fetchCustomerProfile,
  updateCustomerProfile,
} from "@/lib/auth-api";
import { parseProfileUpdateInput } from "@/lib/auth-contract";
import {
  clearAuthCookies,
  privateAuthJson,
  setAuthCookies,
} from "@/lib/auth-route";
import {
  AuthSessionError,
  AuthenticatedOperationError,
  withAuthenticatedSession,
} from "@/lib/authenticated-request";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

function profileError(error: unknown) {
  const rotatedTokens =
    error instanceof AuthenticatedOperationError
      ? error.rotatedTokens
      : undefined;
  const originalError =
    error instanceof AuthenticatedOperationError
      ? error.originalError
      : error;

  if (originalError instanceof AuthSessionError) {
    const response = privateAuthJson(
      { error: "نشست شما منقضی شده است. دوباره وارد شوید." },
      401,
    );
    clearAuthCookies(response);
    return response;
  }

  let response;
  if (originalError instanceof AuthApiError && originalError.status === 400) {
    const payload = originalError.payload;
    const fieldErrors: Record<string, string> = {};
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      if ("first_name" in payload) fieldErrors.first_name = "نام واردشده معتبر نیست.";
      if ("last_name" in payload) fieldErrors.last_name = "نام خانوادگی واردشده معتبر نیست.";
      if ("phone_number" in payload) fieldErrors.phone_number = "شماره تلفن را با قالب بین‌المللی وارد کنید.";
    }
    response = privateAuthJson(
      { error: "اطلاعات پروفایل نیاز به اصلاح دارد.", fieldErrors },
      400,
    );
  } else if (
    originalError instanceof AuthApiError &&
    originalError.status === 404
  ) {
    response = privateAuthJson(
      { error: "این حساب، پروفایل مشتری فروشگاه ندارد." },
      404,
    );
  } else {
    response = privateAuthJson(
      { error: "ارتباط با سرویس حساب کاربری برقرار نشد." },
      503,
    );
  }

  if (rotatedTokens) setAuthCookies(response, rotatedTokens);
  return response;
}

function profileResponse(
  result: Awaited<ReturnType<typeof withAuthenticatedSession>>,
) {
  const response = privateAuthJson(result.value);
  if (result.rotatedTokens) {
    setAuthCookies(response, result.rotatedTokens);
  }
  return response;
}

export async function GET() {
  try {
    return profileResponse(
      await withAuthenticatedSession((access) => fetchCustomerProfile(access)),
    );
  } catch (error) {
    return profileError(error);
  }
}

export async function PATCH(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateAuthJson({ error: "اطلاعات پروفایل معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateAuthJson({ error: "اطلاعات پروفایل معتبر نیست." }, 400);
  }

  const input = parseProfileUpdateInput(payload);
  if (!input) {
    return privateAuthJson(
      { error: "نام‌ها و شماره تلفن را با قالب صحیح وارد کنید." },
      400,
    );
  }

  try {
    return profileResponse(
      await withAuthenticatedSession((access) =>
        updateCustomerProfile(access, input),
      ),
    );
  } catch (error) {
    return profileError(error);
  }
}
