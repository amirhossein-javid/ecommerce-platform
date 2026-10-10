import { privateManagementJson } from "@/lib/management-auth-route";
import { withManagementSession } from "@/lib/management-authenticated-request";
import { fetchManagementOrder } from "@/lib/management-order-api";
import { managementResultResponse, managementRouteError } from "@/lib/management-review-route";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const id = Number((await context.params).id);
  if (!Number.isSafeInteger(id) || id < 1) return privateManagementJson({ error: "شناسهٔ سفارش معتبر نیست." }, 400);
  try {
    return managementResultResponse(
      await withManagementSession((access) => fetchManagementOrder(access, id)),
    );
  } catch (error) {
    return managementRouteError(error);
  }
}
