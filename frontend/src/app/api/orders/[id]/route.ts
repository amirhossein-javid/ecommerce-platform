import { withAuthenticatedSession } from "@/lib/authenticated-request";
import { fetchPaymentOrder } from "@/lib/payment-api";
import { parsePositiveId } from "@/lib/payment-contract";
import { paymentResponse, paymentRouteError } from "@/lib/payment-route";
import { privateJson } from "@/lib/cart-route";

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: Request, context: RouteContext) {
  const orderId = parsePositiveId((await context.params).id);
  if (!orderId) return privateJson({ error: "شناسهٔ سفارش معتبر نیست." }, 400);

  try {
    const result = await withAuthenticatedSession((access) =>
      fetchPaymentOrder(access, orderId),
    );
    return paymentResponse(result.value, result.rotatedTokens);
  } catch (error) {
    return paymentRouteError(error);
  }
}
