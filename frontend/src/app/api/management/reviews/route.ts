import { withManagementSession } from "@/lib/management-authenticated-request";
import { fetchManagedReviews } from "@/lib/management-review-api";
import {
  managementResultResponse,
  managementRouteError,
} from "@/lib/management-review-route";
import { privateManagementJson } from "@/lib/management-auth-route";

function normalizeQuery(request: Request) {
  const input = new URL(request.url).searchParams;
  const output = new URLSearchParams();
  const status = input.get("status");
  if (status && !["PENDING", "APPROVED", "REJECTED"].includes(status)) {
    return null;
  }
  if (status) output.set("status", status);

  const hasReply = input.get("has_reply");
  if (hasReply && hasReply !== "true" && hasReply !== "false") return null;
  if (hasReply) output.set("has_reply", hasReply);

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
  if (query === null) {
    return privateManagementJson({ error: "فیلترهای درخواست معتبر نیستند." }, 400);
  }
  try {
    return managementResultResponse(
      await withManagementSession((access) => fetchManagedReviews(access, query)),
    );
  } catch (error) {
    return managementRouteError(error);
  }
}
