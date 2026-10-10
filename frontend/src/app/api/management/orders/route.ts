import { privateManagementJson } from "@/lib/management-auth-route";
import { withManagementSession } from "@/lib/management-authenticated-request";
import { fetchManagementOrders } from "@/lib/management-order-api";
import { managementResultResponse, managementRouteError } from "@/lib/management-review-route";

function normalizeQuery(request: Request) {
  const input = new URL(request.url).searchParams;
  const output = new URLSearchParams();
  const allowed = ["PENDING_PAYMENT", "PAID", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "EXPIRED"];
  const status = input.get("status");
  if (status && !allowed.includes(status)) return null;
  if (status) output.set("status", status);
  const search = input.get("search")?.trim();
  if (search && search.length > 255) return null;
  if (search) output.set("search", search);
  const page = input.get("page");
  if (page && (!/^\d+$/.test(page) || Number(page) < 1)) return null;
  if (page) output.set("page", page);
  const query = output.toString();
  return query ? `?${query}` : "";
}

export async function GET(request: Request) {
  const query = normalizeQuery(request);
  if (query === null) return privateManagementJson({ error: "فیلترهای سفارش معتبر نیستند." }, 400);
  try {
    return managementResultResponse(
      await withManagementSession((access) => fetchManagementOrders(access, query)),
    );
  } catch (error) {
    return managementRouteError(error);
  }
}
