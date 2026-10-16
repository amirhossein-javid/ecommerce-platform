import { privateManagementJson } from "@/lib/management-auth-route";
import { withManagementSession } from "@/lib/management-authenticated-request";
import { parseShipment } from "@/lib/management-order-contract";
import { updateManagementShipment } from "@/lib/management-order-api";
import { managementResultResponse, managementRouteError } from "@/lib/management-review-route";
import { hasJsonContentType, isTrustedMutationRequest } from "@/lib/cart-security";

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> }) {
  if (!isTrustedMutationRequest(request.url, request.headers)) return privateManagementJson({ error: "درخواست غیرمجاز است." }, 403);
  if (!hasJsonContentType(request.headers)) return privateManagementJson({ error: "اطلاعات مرسوله معتبر نیست." }, 400);
  const id = Number((await context.params).id);
  if (!Number.isSafeInteger(id) || id < 1) return privateManagementJson({ error: "شناسهٔ سفارش معتبر نیست." }, 400);
  let raw: unknown;
  try { raw = await request.json(); } catch { return privateManagementJson({ error: "اطلاعات مرسوله معتبر نیست." }, 400); }
  const input = parseShipment(raw);
  if (!input) return privateManagementJson({ error: "حامل و کد رهگیری معتبر وارد کنید." }, 400);
  try {
    return managementResultResponse(await withManagementSession((access) => updateManagementShipment(access, id, input.carrier, input.tracking_number)));
  } catch (error) { return managementRouteError(error); }
}
