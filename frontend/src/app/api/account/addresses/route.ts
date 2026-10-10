import {
  createCustomerAddress,
  fetchCustomerAddresses,
} from "@/lib/auth-api";
import { parseAddressInput } from "@/lib/address-contract";
import { addressResponse, addressRouteError } from "@/lib/address-route";
import { privateAuthJson } from "@/lib/auth-route";
import { withAuthenticatedSession } from "@/lib/authenticated-request";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

export async function GET() {
  try {
    const result = await withAuthenticatedSession(fetchCustomerAddresses);
    return addressResponse(result.value, result.rotatedTokens);
  } catch (error) {
    return addressRouteError(error);
  }
}

export async function POST(request: Request) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateAuthJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
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
      createCustomerAddress(access, input),
    );
    return addressResponse(result.value, result.rotatedTokens, 201);
  } catch (error) {
    return addressRouteError(error);
  }
}
