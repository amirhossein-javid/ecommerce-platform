import {
  deleteCustomerAddress,
  updateCustomerAddress,
} from "@/lib/auth-api";
import { parseAddressId, parseAddressInput } from "@/lib/address-contract";
import { addressResponse, addressRouteError } from "@/lib/address-route";
import { privateAuthJson } from "@/lib/auth-route";
import { withAuthenticatedSession } from "@/lib/authenticated-request";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

type RouteContext = { params: Promise<{ id: string }> };

async function getAddressId(context: RouteContext) {
  return parseAddressId((await context.params).id);
}

export async function PATCH(request: Request, context: RouteContext) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  const id = await getAddressId(context);
  if (!id || !hasJsonContentType(request.headers)) {
    return privateAuthJson({ error: "اطلاعات آدرس معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateAuthJson({ error: "اطلاعات آدرس معتبر نیست." }, 400);
  }
  const input = parseAddressInput(payload);
  if (!input) {
    return privateAuthJson(
      { error: "فیلدهای آدرس را کامل و با قالب صحیح وارد کنید." },
      400,
    );
  }

  try {
    const result = await withAuthenticatedSession((access) =>
      updateCustomerAddress(access, id, input),
    );
    return addressResponse(result.value, result.rotatedTokens);
  } catch (error) {
    return addressRouteError(error);
  }
}

export async function DELETE(request: Request, context: RouteContext) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  const id = await getAddressId(context);
  if (!id) return privateAuthJson({ error: "شناسهٔ آدرس معتبر نیست." }, 400);

  try {
    const result = await withAuthenticatedSession((access) =>
      deleteCustomerAddress(access, id),
    );
    return addressResponse({ deleted: true }, result.rotatedTokens);
  } catch (error) {
    return addressRouteError(error);
  }
}
