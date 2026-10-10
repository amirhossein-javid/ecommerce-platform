import { withAuthenticatedSession } from "@/lib/authenticated-request";
import { privateJson } from "@/lib/cart-route";
import { initiateOrderPayment } from "@/lib/payment-api";
import {
  parseEmptyPaymentInput,
  parsePositiveId,
} from "@/lib/payment-contract";
import { paymentResponse, paymentRouteError } from "@/lib/payment-route";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(request: Request, context: RouteContext) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateJson({ error: "درخواست پرداخت معتبر نیست." }, 400);
  }
  const orderId = parsePositiveId((await context.params).id);
  if (!orderId) return privateJson({ error: "شناسهٔ سفارش معتبر نیست." }, 400);

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateJson({ error: "درخواست پرداخت معتبر نیست." }, 400);
  }
  if (!parseEmptyPaymentInput(payload)) {
    return privateJson({ error: "درخواست پرداخت نباید شامل مبلغ یا اطلاعات اضافی باشد." }, 400);
  }

  try {
    const result = await withAuthenticatedSession((access) =>
      initiateOrderPayment(access, orderId),
    );
    return paymentResponse(result.value, result.rotatedTokens);
  } catch (error) {
    return paymentRouteError(error);
  }
}
