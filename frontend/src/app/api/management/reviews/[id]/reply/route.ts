import { privateManagementJson } from "@/lib/management-auth-route";
import { withManagementSession } from "@/lib/management-authenticated-request";
import { parseStoreReplyInput } from "@/lib/management-review-contract";
import {
  deleteManagedReply,
  saveManagedReply,
} from "@/lib/management-review-api";
import {
  managementResultResponse,
  managementRouteError,
} from "@/lib/management-review-route";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

async function parseRequest(request: Request, rawId: string) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return { response: privateManagementJson({ error: "درخواست غیرمجاز است." }, 403) };
  }
  if (!hasJsonContentType(request.headers)) {
    return { response: privateManagementJson({ error: "متن پاسخ معتبر نیست." }, 400) };
  }
  const id = Number(rawId);
  if (!Number.isSafeInteger(id) || id < 1) {
    return { response: privateManagementJson({ error: "شناسهٔ نظر معتبر نیست." }, 400) };
  }
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return { response: privateManagementJson({ error: "متن پاسخ معتبر نیست." }, 400) };
  }
  const input = parseStoreReplyInput(payload);
  if (!input) {
    return { response: privateManagementJson({ error: "متن پاسخ معتبر نیست." }, 400) };
  }
  return { id, input };
}

async function save(
  request: Request,
  context: { params: Promise<{ id: string }> },
  exists: boolean,
) {
  const { id: rawId } = await context.params;
  const parsed = await parseRequest(request, rawId);
  if ("response" in parsed) return parsed.response;
  try {
    return managementResultResponse(
      await withManagementSession((access) =>
        saveManagedReply(access, parsed.id, parsed.input.comment, exists),
      ),
    );
  } catch (error) {
    return managementRouteError(error);
  }
}

export function POST(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  return save(request, context, false);
}

export function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  return save(request, context, true);
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateManagementJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  const { id: rawId } = await context.params;
  const id = Number(rawId);
  if (!Number.isSafeInteger(id) || id < 1) {
    return privateManagementJson({ error: "شناسهٔ نظر معتبر نیست." }, 400);
  }
  try {
    const result = await withManagementSession((access) =>
      deleteManagedReply(access, id),
    );
    return managementResultResponse({
      value: { deleted: true },
      rotatedTokens: result.rotatedTokens,
    });
  } catch (error) {
    return managementRouteError(error);
  }
}
