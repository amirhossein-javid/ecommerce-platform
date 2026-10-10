"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { isCheckoutOrder, type OrderStatus } from "@/lib/checkout-contract";
import {
  type CallbackData,
  isPaymentAttempt,
  type PaymentStatus,
} from "@/lib/payment-contract";
import { ORDER_STATUS_LABELS } from "@/lib/order-policy";

type PaymentReturnViewProps = {
  callbackData: CallbackData | null;
  orderId: number;
  paymentId: number;
};

export function PaymentReturnView({ callbackData, orderId, paymentId }: PaymentReturnViewProps) {
  const router = useRouter();
  const started = useRef(false);
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus>();
  const [orderStatus, setOrderStatus] = useState<OrderStatus>();
  const [error, setError] = useState(callbackData ? "" : "اطلاعات بازگشت از درگاه معتبر نیست.");
  const [pending, setPending] = useState(Boolean(callbackData));

  useEffect(() => {
    if (!callbackData || started.current) return;
    started.current = true;
    let active = true;

    const verify = async () => {
      try {
        const response = await fetch(
          `/api/orders/${orderId}/payments/${paymentId}/verify`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ callbackData }),
          },
        );
        if (response.status === 401) {
          router.push("/login");
          router.refresh();
          return;
        }
        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as { error?: unknown } | null;
          if (active) setError(typeof payload?.error === "string" ? payload.error : "تأیید پرداخت ممکن نشد.");
        } else {
          const payload: unknown = await response.json();
          if (!isPaymentAttempt(payload)) throw new Error("payment");
          if (active) setPaymentStatus(payload.status);
        }

        const orderResponse = await fetch(`/api/orders/${orderId}`, { cache: "no-store" });
        if (orderResponse.status === 401) {
          router.push("/login");
          router.refresh();
          return;
        }
        if (orderResponse.ok) {
          const orderPayload: unknown = await orderResponse.json();
          if (isCheckoutOrder(orderPayload) && active) setOrderStatus(orderPayload.status);
        }
      } catch {
        if (active) setError("ارتباط برای تأیید پرداخت برقرار نشد. تکرار این بررسی امن است.");
      } finally {
        if (active) setPending(false);
      }
    };
    void verify();
    return () => {
      active = false;
    };
  }, [callbackData, orderId, paymentId, router]);

  const success = paymentStatus === "SUCCESS" && orderStatus === "PAID";
  const lateSuccess = paymentStatus === "SUCCESS" && (orderStatus === "EXPIRED" || orderStatus === "CANCELLED");

  return (
    <section className="mx-auto max-w-2xl rounded-xl border border-border/75 bg-surface px-5 py-10 text-center sm:px-8 sm:py-12" aria-live="polite">
      <div className={`mx-auto grid size-14 place-items-center rounded-xl text-2xl font-black ${success ? "bg-success-soft text-success" : "bg-primary-soft text-primary"}`} aria-hidden="true">{success ? "✓" : "…"}</div>
      <h1 className="mt-5 text-2xl font-black text-foreground">{pending ? "در حال بررسی پرداخت" : success ? "پرداخت تأیید شد" : lateSuccess ? "پرداخت برای سفارش بسته ثبت شده است" : paymentStatus === "FAILED" ? "پرداخت ناموفق بود" : "نتیجه پرداخت نیاز به بررسی دارد"}</h1>
      <p className="mt-3 leading-8 text-muted-foreground">{pending ? "اطلاعات بازگشت برای تأیید به Django ارسال شده است." : success ? "وضعیت پرداخت و سفارش هر دو توسط فروشگاه تأیید شده‌اند." : lateSuccess ? "سفارش منقضی یا لغو شده باقی می‌ماند؛ وضعیت سفارش را برای ادامه بررسی کنید." : "وضعیت نمایش‌داده‌شده از پاسخ authoritative فروشگاه دریافت شده است."}</p>
      {error ? <p role="alert" className="mt-5 rounded-lg bg-destructive-soft px-4 py-3 text-sm font-semibold leading-7 text-destructive">{error}</p> : null}
      {orderStatus ? <p className="mt-4 text-sm font-bold text-primary">وضعیت سفارش: {ORDER_STATUS_LABELS[orderStatus]}</p> : null}
      <Link href={`/account/orders/${orderId}`} className="mt-7 inline-flex min-h-12 items-center justify-center rounded-lg bg-primary px-6 text-sm font-extrabold text-primary-foreground hover:bg-primary-hover">مشاهدهٔ جزئیات سفارش</Link>
    </section>
  );
}
