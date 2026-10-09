import { loginCustomer } from "@/lib/auth-api";
import { parseLoginInput } from "@/lib/auth-contract";
import {
  authRouteError,
  privateAuthJson,
  setAuthCookies,
} from "@/lib/auth-route";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

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
    const response = privateAuthJson({ authenticated: true });
    setAuthCookies(response, tokens);
    return response;
  } catch (error) {
    return authRouteError(error, "login");
  }
}
