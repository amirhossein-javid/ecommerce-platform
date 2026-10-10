"use client";

import Link from "next/link";
import Script from "next/script";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { isCheckoutOrder, type OrderStatus } from "@/lib/checkout-contract";
import { isPaymentAttempt, type PaymentStatus } from "@/lib/payment-contract";
import { canRetryPayment } from "@/lib/payment-policy";

declare global {
  interface Window {
    Bale?: {
      WebApp?: {
        ready?: () => void;
        openInvoice?: (
          identifier: string,
          callback: (result?: { status?: unknown }) => void,
        ) => void;
      };
    };
  }
}

type PaymentPanelProps = {
  orderId: number;
  initialOrderStatus: OrderStatus;
};

const TERMINAL_LABELS: Partial<Record<OrderStatus, string>> = {
  PAID: "پرداخت سفارش با موفقیت در فروشگاه تأیید شده است.",
  CANCELLED: "این سفارش لغو شده و قابل پرداخت نیست.",
  EXPIRED: "مهلت پرداخت این سفارش به پایان رسیده است.",
  PROCESSING: "پرداخت تأیید شده و سفارش در حال پردازش است.",
  SHIPPED: "سفارش پرداخت و ارسال شده است.",
  DELIVERED: "سفارش پرداخت و تحویل شده است.",
};

async function responseError(response: Response) {
  try {
    const payload = (await response.json()) as { error?: unknown; code?: unknown };
    return {
      message:
        typeof payload.error === "string"
          ? payload.error
          : "درخواست پرداخت انجام نشد.",
      code: typeof payload.code === "string" ? payload.code : undefined,
    };
  } catch {
    return { message: "درخواست پرداخت انجام نشد.", code: undefined };
  }
}

export function PaymentPanel({ orderId, initialOrderStatus }: PaymentPanelProps) {
  const router = useRouter();
  const lock = useRef(false);
  const [orderStatus, setOrderStatus] = useState(initialOrderStatus);
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus>();
  const [pending, setPending] = useState(false);
  const [checking, setChecking] = useState(false);
  const [baleReady, setBaleReady] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const readOrder = async () => {
    const response = await fetch(`/api/orders/${orderId}`, { cache: "no-store" });
    if (response.status === 401) {
      router.push("/login");
      router.refresh();
      return null;
    }
    if (!response.ok) throw new Error("order");
    const payload: unknown = await response.json();
    if (!isCheckoutOrder(payload)) throw new Error("order");
    setOrderStatus(payload.status);
    if (payload.status !== "PENDING_PAYMENT") router.refresh();
    return payload.status;
  };

  const checkOrder = async (attempts = 1) => {
    if (checking) return;
    setChecking(true);
    setError("");
    try {
      for (let index = 0; index < attempts; index += 1) {
        const status = await readOrder();
        if (!status || status !== "PENDING_PAYMENT") return;
        if (index < attempts - 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 2_000));
        }
      }
      setMessage("پرداخت هنوز از سوی فروشگاه تأیید نشده است. کمی بعد دوباره وضعیت را بررسی کنید.");
    } catch {
      setError("دریافت وضعیت سفارش ممکن نشد. کمی بعد دوباره تلاش کنید.");
    } finally {
      setChecking(false);
    }
  };

  const openBaleInvoice = (identifier: string) => {
    const webApp = window.Bale?.WebApp;
    if (!baleReady || !webApp?.openInvoice) {
      setError("باز کردن پرداخت بله فقط داخل مینی‌اپ بله در دسترس است.");
      lock.current = false;
      return;
    }
    setMessage("صورتحساب بله باز شد. نتیجه نهایی از سرور فروشگاه بررسی می‌شود.");
    try {
      webApp.openInvoice(identifier, (result) => {
        const status = result?.status;
        if (status === "cancelled") {
          setMessage("پنجره پرداخت بسته شد؛ وضعیت واقعی سفارش در حال بررسی است.");
        } else if (status === "failed") {
          setMessage("درگاه نتیجه ناموفق گزارش کرد؛ وضعیت واقعی سفارش در حال بررسی است.");
        } else {
          setMessage("وضعیت پرداخت در حال بررسی با سرور فروشگاه است.");
        }
        lock.current = false;
        void checkOrder(6);
      });
    } catch {
      setError("باز کردن صورتحساب بله ممکن نشد.");
      lock.current = false;
    }
  };

  const initiate = async () => {
    if (lock.current || !canRetryPayment(orderStatus, paymentStatus)) return;
    lock.current = true;
    setPending(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`/api/orders/${orderId}/payments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (response.status === 401) {
        router.push("/login");
        router.refresh();
        return;
      }
      if (!response.ok) {
        const failure = await responseError(response);
        setError(failure.message);
        if (failure.code === "expired" || failure.code === "not-payable") {
          await checkOrder();
        }
        lock.current = false;
        return;
      }

      const payload: unknown = await response.json();
      if (!isPaymentAttempt(payload)) {
        setError("پاسخ آغاز پرداخت معتبر نبود. وضعیت سفارش را بررسی کنید.");
        lock.current = false;
        return;
      }
      setPaymentStatus(payload.status);
      if (payload.status !== "PENDING") {
        await checkOrder();
        lock.current = false;
        return;
      }
      if (payload.payment_url) {
        window.location.assign(payload.payment_url);
        return;
      }
      if (payload.payment_identifier) {
        openBaleInvoice(payload.payment_identifier);
        return;
      }
      setError("درگاه مسیر ادامهٔ پرداخت را برنگرداند.");
      lock.current = false;
    } catch {
      setError("پاسخ آغاز پرداخت دریافت نشد. می‌توانید دوباره تلاش کنید؛ فروشگاه درخواست تکراری را به‌صورت ایمن مدیریت می‌کند.");
      lock.current = false;
    } finally {
      setPending(false);
    }
  };

  const terminalMessage = TERMINAL_LABELS[orderStatus];
  const retryAllowed = canRetryPayment(orderStatus, paymentStatus);

  return (
    <section aria-labelledby="payment-action-title" className="mt-5 border-t border-gold/30 pt-5">
      <Script
        src="https://tapi.bale.ai/miniapp.js"
        strategy="afterInteractive"
        onLoad={() => {
          window.Bale?.WebApp?.ready?.();
          setBaleReady(Boolean(window.Bale?.WebApp?.openInvoice));
        }}
      />
      <h3 id="payment-action-title" className="font-black text-foreground">پرداخت سفارش</h3>
      {terminalMessage ? (
        <p className={`mt-3 rounded-xl border px-3 py-3 text-xs font-semibold leading-6 ${orderStatus === "PAID" || orderStatus === "PROCESSING" || orderStatus === "SHIPPED" || orderStatus === "DELIVERED" ? "border-success/20 bg-success-soft text-success" : "border-destructive/20 bg-destructive-soft text-destructive"}`} role="status">
          {terminalMessage}
        </p>
      ) : (
        <p className="mt-2 text-xs leading-6 text-muted-foreground">پس از بازگشت از درگاه، فقط وضعیت ثبت‌شده در فروشگاه ملاک نتیجه است.</p>
      )}
      {message ? <p className="mt-3 rounded-xl border border-primary/15 bg-primary-soft/55 px-3 py-3 text-xs font-semibold leading-6 text-foreground" role="status">{message}</p> : null}
      {error ? <p className="mt-3 rounded-xl border border-destructive/20 bg-destructive-soft px-3 py-3 text-xs font-semibold leading-6 text-destructive" role="alert">{error}</p> : null}

      {retryAllowed ? (
        <button type="button" onClick={initiate} disabled={pending || checking} className="mt-4 inline-flex min-h-12 w-full items-center justify-center rounded-full bg-primary px-5 text-sm font-extrabold text-primary-foreground shadow-[0_14px_30px_-18px_rgb(8_108_104/0.85)] hover:bg-primary-hover disabled:cursor-wait disabled:opacity-60">
          {pending ? "در حال اتصال به درگاه…" : "پرداخت سفارش"}
        </button>
      ) : null}
      {orderStatus === "PENDING_PAYMENT" ? (
        <button type="button" onClick={() => void checkOrder()} disabled={checking || pending} className="mt-2 inline-flex min-h-11 w-full items-center justify-center rounded-full border border-primary/30 px-4 text-sm font-bold text-primary hover:bg-primary-soft/50 disabled:opacity-60">
          {checking ? "در حال بررسی…" : "بررسی وضعیت پرداخت"}
        </button>
      ) : null}
      {orderStatus === "EXPIRED" || orderStatus === "CANCELLED" ? (
        <Link href="/products" className="mt-3 inline-flex min-h-11 w-full items-center justify-center text-sm font-bold text-primary hover:underline">بازگشت به محصولات</Link>
      ) : null}
    </section>
  );
}
