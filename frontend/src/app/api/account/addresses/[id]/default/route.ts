import { setDefaultCustomerAddress } from "@/lib/auth-api";
import { parseAddressId } from "@/lib/address-contract";
import { addressResponse, addressRouteError } from "@/lib/address-route";
import { privateAuthJson } from "@/lib/auth-route";
import { withAuthenticatedSession } from "@/lib/authenticated-request";
import { isTrustedMutationRequest } from "@/lib/cart-security";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(request: Request, context: RouteContext) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  const id = parseAddressId((await context.params).id);
  if (!id) return privateAuthJson({ error: "شناسهٔ آدرس معتبر نیست." }, 400);

  try {
    const result = await withAuthenticatedSession((access) =>
      setDefaultCustomerAddress(access, id),
    );
    return addressResponse(result.value, result.rotatedTokens);
  } catch (error) {
    return addressRouteError(error);
  }
}
