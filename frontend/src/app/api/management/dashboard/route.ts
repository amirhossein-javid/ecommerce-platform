import { withManagementSession } from "@/lib/management-authenticated-request";
import { fetchManagementSummary } from "@/lib/management-order-api";
import { managementResultResponse, managementRouteError } from "@/lib/management-review-route";

export async function GET() {
  try {
    return managementResultResponse(
      await withManagementSession((access) => fetchManagementSummary(access)),
    );
  } catch (error) {
    return managementRouteError(error);
  }
}
