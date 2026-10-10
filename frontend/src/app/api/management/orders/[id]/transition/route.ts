import { privateManagementJson } from "@/lib/management-auth-route";
import { withManagementSession } from "@/lib/management-authenticated-request";
import { parseTransition } from "@/lib/management-order-contract";
import { transitionManagementOrder } from "@/lib/management-order-api";
import { managementResultResponse, managementRouteError } from "@/lib/management-review-route";
import { hasJsonContentType, isTrustedMutationRequest } from "@/lib/cart-security";

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  if (!isTrustedMutationRequest(request.url, request.headers)) return privateManagementJson({ error: "درخواست غیرمجاز است." }, 403);
  if (!hasJsonContentType(request.headers)) return privateManagementJson({ error: "وضعیت سفارش معتبر نیست." }, 400);
  const id = Number((await context.params).id);
  if (!Number.isSafeInteger(id) || id < 1) return privateManagementJson({ error: "شناسهٔ سفارش معتبر نیست." }, 400);
  let raw: unknown;
  try { raw = await request.json(); } catch { return privateManagementJson({ error: "وضعیت سفارش معتبر نیست." }, 400); }
  const input = parseTransition(raw);
  if (!input) return privateManagementJson({ error: "گذار وضعیت سفارش معتبر نیست." }, 400);
  try {
    return managementResultResponse(await withManagementSession((access) => transitionManagementOrder(access, id, input.status)));
  } catch (error) { return managementRouteError(error); }
}
