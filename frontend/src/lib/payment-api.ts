import "server-only";

import { type CheckoutOrder, isCheckoutOrder } from "@/lib/checkout-contract";
import {
  type CallbackData,
  type PaymentAttempt,
  parsePaymentAttempt,
} from "@/lib/payment-contract";
import { validatePaymentRedirect } from "@/lib/payment-redirect-policy";

const ORDERS_PATH = "/api/v1/orders/";

export class PaymentApiError extends Error {
  constructor(
    public readonly status?: number,
    public readonly payload?: unknown,
    public readonly retryAfter?: string | null,
  ) {
    super("The payment API request failed.");
    this.name = "PaymentApiError";
  }
}

export class PaymentHandoffError extends Error {
  constructor() {
    super("The payment handoff destination is not trusted.");
    this.name = "PaymentHandoffError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;
  if (!value) throw new PaymentApiError();
  try {
    return new URL(value);
  } catch {
    throw new PaymentApiError();
  }
}

async function parsePayload(response: Response) {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

async function requestDjango(path: string, access: string, init: RequestInit) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${access}`);

  let response: Response;
  try {
    response = await fetch(new URL(path, getApiOrigin()), {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new PaymentApiError();
  }

  if (!response.ok) {
    throw new PaymentApiError(
      response.status,
      await parsePayload(response),
      response.headers.get("retry-after"),
    );
  }
  return response;
}

export function trustedPaymentUrl(value: string) {
  const trusted = validatePaymentRedirect(
    value,
    process.env.PAYMENT_REDIRECT_ALLOWED_ORIGINS ?? "",
  );
  if (!trusted) throw new PaymentHandoffError();
  return trusted;
}

async function parseAttemptResponse(response: Response): Promise<PaymentAttempt> {
  const attempt = parsePaymentAttempt(await parsePayload(response));
  if (!attempt) throw new PaymentApiError();
  return attempt.payment_url
    ? { ...attempt, payment_url: trustedPaymentUrl(attempt.payment_url) }
    : attempt;
}

export async function initiateOrderPayment(access: string, orderId: number) {
  return parseAttemptResponse(
    await requestDjango(`${ORDERS_PATH}${orderId}/payments/`, access, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    }),
  );
}

export async function verifyOrderPayment(
  access: string,
  orderId: number,
  paymentId: number,
  callbackData: CallbackData,
) {
  return parseAttemptResponse(
    await requestDjango(
      `${ORDERS_PATH}${orderId}/payments/${paymentId}/verify/`,
      access,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ callback_data: callbackData }),
      },
    ),
  );
}

export async function fetchPaymentOrder(
  access: string,
  orderId: number,
): Promise<CheckoutOrder> {
  const response = await requestDjango(`${ORDERS_PATH}${orderId}/`, access, {
    method: "GET",
  });
  const payload = await parsePayload(response);
  if (!isCheckoutOrder(payload)) throw new PaymentApiError();
  return payload;
}
