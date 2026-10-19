import { registerCustomer } from "@/lib/auth-api";
import { parseRegistrationInput } from "@/lib/auth-contract";
import { authRouteError, privateAuthJson } from "@/lib/auth-route";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";
import { trustedClientIp } from "@/lib/client-identity";

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateAuthJson({ error: "اطلاعات ثبت‌نام معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateAuthJson({ error: "اطلاعات ثبت‌نام معتبر نیست." }, 400);
  }

  const input = parseRegistrationInput(payload);
  if (!input) {
    return privateAuthJson(
      { error: "همهٔ اطلاعات را با قالب صحیح وارد کنید." },
      400,
    );
  }

  try {
    await registerCustomer(input, trustedClientIp(request.headers));
    return privateAuthJson({ registered: true }, 201);
  } catch (error) {
    return authRouteError(error, "register");
  }
}
