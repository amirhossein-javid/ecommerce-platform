import { privateManagementJson } from "@/lib/management-auth-route";
import { withManagementSession } from "@/lib/management-authenticated-request";
import { parseModerationInput } from "@/lib/management-review-contract";
import { moderateManagedReview } from "@/lib/management-review-api";
import {
  managementResultResponse,
  managementRouteError,
} from "@/lib/management-review-route";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateManagementJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateManagementJson({ error: "اطلاعات بررسی معتبر نیست." }, 400);
  }
  const { id: rawId } = await context.params;
  const id = Number(rawId);
  if (!Number.isSafeInteger(id) || id < 1) {
    return privateManagementJson({ error: "شناسهٔ نظر معتبر نیست." }, 400);
  }
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateManagementJson({ error: "اطلاعات بررسی معتبر نیست." }, 400);
  }
  const input = parseModerationInput(payload);
  if (!input) {
    return privateManagementJson({ error: "وضعیت بررسی معتبر نیست." }, 400);
  }
  try {
    return managementResultResponse(
      await withManagementSession((access) =>
        moderateManagedReview(access, id, input.status),
      ),
    );
  } catch (error) {
    return managementRouteError(error);
  }
}
