import { privateManagementJson } from "@/lib/management-auth-route";
import { withManagementSession } from "@/lib/management-authenticated-request";
import { resolveManagementRefund } from "@/lib/management-order-api";
import { managementResultResponse, managementRouteError } from "@/lib/management-review-route";
import { isTrustedMutationRequest } from "@/lib/cart-security";

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  if (!isTrustedMutationRequest(request.url, request.headers)) return privateManagementJson({ error: "درخواست غیرمجاز است." }, 403);
  const id = Number((await context.params).id);
  if (!Number.isSafeInteger(id) || id < 1) return privateManagementJson({ error: "شناسهٔ سفارش معتبر نیست." }, 400);
  try {
    return managementResultResponse(await withManagementSession((access) => resolveManagementRefund(access, id)));
  } catch (error) { return managementRouteError(error); }
}
