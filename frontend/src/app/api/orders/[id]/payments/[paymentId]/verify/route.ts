import { withAuthenticatedSession } from "@/lib/authenticated-request";
import { privateJson } from "@/lib/cart-route";
import { verifyOrderPayment } from "@/lib/payment-api";
import {
  parsePositiveId,
  parseVerificationInput,
} from "@/lib/payment-contract";
import { paymentResponse, paymentRouteError } from "@/lib/payment-route";
import {
  hasJsonContentType,
  isTrustedMutationRequest,
} from "@/lib/cart-security";

type RouteContext = {
  params: Promise<{ id: string; paymentId: string }>;
};

export async function POST(request: Request, context: RouteContext) {
  if (!isTrustedMutationRequest(request.url, request.headers)) {
    return privateJson({ error: "درخواست غیرمجاز است." }, 403);
  }
  if (!hasJsonContentType(request.headers)) {
    return privateJson({ error: "اطلاعات بازگشت از درگاه معتبر نیست." }, 400);
  }
  const params = await context.params;
  const orderId = parsePositiveId(params.id);
  const paymentId = parsePositiveId(params.paymentId);
  if (!orderId || !paymentId) {
    return privateJson({ error: "شناسهٔ سفارش یا پرداخت معتبر نیست." }, 400);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return privateJson({ error: "اطلاعات بازگشت از درگاه معتبر نیست." }, 400);
  }
  const input = parseVerificationInput(payload);
  if (!input) {
    return privateJson({ error: "اطلاعات بازگشت از درگاه معتبر نیست." }, 400);
  }

  try {
    const result = await withAuthenticatedSession((access) =>
      verifyOrderPayment(access, orderId, paymentId, input.callbackData),
    );
    return paymentResponse(result.value, result.rotatedTokens);
  } catch (error) {
    return paymentRouteError(error);
  }
}
