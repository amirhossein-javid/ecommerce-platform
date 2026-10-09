import { clearAuthCookies, privateAuthJson } from "@/lib/auth-route";
import { getCustomerSession } from "@/lib/auth-session";

export async function GET() {
  const session = await getCustomerSession();
  if (session.state === "customer") {
    return privateAuthJson({ authenticated: true, customer: session.customer });
  }
  if (session.state === "missing-profile") {
    return privateAuthJson(
      {
        authenticated: true,
        customer: null,
        accountState: "missing_profile",
        error: "این حساب، پروفایل مشتری فروشگاه ندارد.",
      },
      403,
    );
  }
  if (session.state === "invalid") {
    const response = privateAuthJson(
      { authenticated: false, customer: null, error: "نشست شما منقضی شده است." },
      401,
    );
    clearAuthCookies(response);
    return response;
  }
  if (session.state === "upstream-error") {
    return privateAuthJson(
      { error: "بررسی وضعیت حساب ممکن نشد." },
      503,
    );
  }
  return privateAuthJson({ authenticated: false, customer: null });
}
