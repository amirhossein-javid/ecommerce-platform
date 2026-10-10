import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Container } from "@/components/container";
import { PaymentReturnView } from "@/components/payment-return-view";
import { getCustomerSession } from "@/lib/auth-session";
import {
  type CallbackData,
  parsePositiveId,
  parseVerificationInput,
} from "@/lib/payment-contract";

export const metadata: Metadata = {
  title: "نتیجهٔ پرداخت | نقش‌جهان",
  description: "بررسی نتیجهٔ پرداخت سفارش با وضعیت ثبت‌شده در فروشگاه",
};

type PaymentReturnPageProps = {
  params: Promise<{ orderId: string; paymentId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function callbackFromSearchParams(
  values: Record<string, string | string[] | undefined>,
): CallbackData | null {
  const callbackData = Object.fromEntries(
    Object.entries(values).filter((entry): entry is [string, string | string[]] =>
      entry[1] !== undefined,
    ),
  );
  return parseVerificationInput({ callbackData })?.callbackData ?? null;
}

export default async function PaymentReturnPage({
  params,
  searchParams,
}: PaymentReturnPageProps) {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") {
    redirect("/login");
  }
  if (session.state === "missing-profile") redirect("/account");

  const routeParams = await params;
  const orderId = parsePositiveId(routeParams.orderId);
  const paymentId = parsePositiveId(routeParams.paymentId);
  if (!orderId || !paymentId) notFound();

  if (session.state === "upstream-error") {
    return (
      <Container className="py-12 sm:py-16">
        <section
          role="alert"
          className="mx-auto max-w-2xl rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-5 py-12 text-center"
        >
          <h1 className="text-2xl font-black text-foreground">
            بررسی نشست مشتری ممکن نشد
          </h1>
          <p className="mt-3 leading-8 text-muted-foreground">
            نتیجهٔ پرداخت حدس زده نمی‌شود. پس از برقراری سرویس، وضعیت سفارش را
            دوباره بررسی کنید.
          </p>
          <Link
            href={`/account/orders/${orderId}`}
            className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover"
          >
            مشاهدهٔ وضعیت سفارش
          </Link>
        </section>
      </Container>
    );
  }

  const callbackData = callbackFromSearchParams(await searchParams);

  return (
    <Container className="py-7 sm:py-12 lg:py-16">
      <PaymentReturnView
        callbackData={callbackData}
        orderId={orderId}
        paymentId={paymentId}
      />
    </Container>
  );
}
