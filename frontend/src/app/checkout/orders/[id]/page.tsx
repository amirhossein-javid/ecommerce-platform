import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Container } from "@/components/container";
import { getCustomerSession } from "@/lib/auth-session";
import { CheckoutApiError, getCustomerOrder } from "@/lib/checkout-api";
import { parseOrderId, type OrderStatus } from "@/lib/checkout-contract";
import { formatToman } from "@/lib/format-price";

export const metadata: Metadata = {
  title: "نتیجهٔ ثبت سفارش | فروشگاه",
  description: "مشاهدهٔ نتیجه و وضعیت واقعی سفارش",
};

const STATUS_LABELS: Record<OrderStatus, string> = {
  PENDING_PAYMENT: "در انتظار پرداخت",
  PAID: "پرداخت‌شده",
  PROCESSING: "در حال پردازش",
  SHIPPED: "ارسال‌شده",
  DELIVERED: "تحویل‌شده",
  CANCELLED: "لغوشده",
  EXPIRED: "منقضی‌شده",
};

type OrderResultPageProps = {
  params: Promise<{ id: string }>;
};

export default async function OrderResultPage({ params }: OrderResultPageProps) {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") redirect("/login");
  if (session.state === "missing-profile") redirect("/account");

  const orderId = parseOrderId((await params).id);
  if (!orderId) notFound();

  let order;
  try {
    order = await getCustomerOrder(orderId);
  } catch (error) {
    if (error instanceof CheckoutApiError && error.status === 404) notFound();
    return (
      <Container className="py-10 sm:py-16">
        <section role="alert" className="mx-auto max-w-2xl rounded-xl bg-destructive-soft/45 px-5 py-12 text-center">
          <h1 className="text-2xl font-black text-foreground">دریافت وضعیت سفارش ممکن نشد</h1>
          <p className="mt-3 leading-8 text-muted-foreground">ارتباط با سرویس سفارش‌ها برقرار نشد. کمی بعد دوباره تلاش کنید.</p>
          <Link href={`/checkout/orders/${orderId}`} className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">تلاش دوباره</Link>
        </section>
      </Container>
    );
  }

  return (
    <Container className="py-7 sm:py-10 lg:py-14">
      <section className="mx-auto max-w-5xl">
        <header className="border-b border-border/75 pb-7">
          <div className="grid size-14 place-items-center rounded-xl bg-success-soft text-2xl font-black text-success" aria-hidden="true">✓</div>
          <p className="mt-5 text-sm font-bold text-primary">سفارش با موفقیت ثبت شد</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-foreground sm:text-4xl">سفارش شمارهٔ <bdi>{order.id.toLocaleString("fa-IR")}</bdi></h1>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className="rounded-lg bg-primary-soft px-3 py-2 text-sm font-bold text-primary">وضعیت واقعی: {STATUS_LABELS[order.status]}</span>
            {order.status === "PENDING_PAYMENT" ? <span className="text-sm font-semibold text-muted-foreground">پرداخت هنوز انجام نشده است.</span> : null}
          </div>
        </header>

        <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start xl:gap-10">
          <div className="min-w-0 space-y-8">
            <section aria-labelledby="result-items-title">
              <h2 id="result-items-title" className="border-b border-border/75 pb-4 text-xl font-black text-foreground">کالاهای سفارش</h2>
              <div className="divide-y divide-border/75">
                {order.items.map((item, index) => (
                  <article key={item.id ?? `${item.sku}-${index}`} className="py-5">
                    <h3 className="text-sm font-extrabold leading-7 text-foreground sm:text-base">{item.product_name}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">کد کالا: <bdi>{item.sku}</bdi></p>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
                      <span className="text-muted-foreground">تعداد: <bdi className="font-bold text-foreground">{item.quantity.toLocaleString("fa-IR")}</bdi></span>
                      <strong className="tabular-nums text-primary"><bdi>{formatToman(item.line_total)}</bdi></strong>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section aria-labelledby="shipping-snapshot-title" className="rounded-xl bg-surface-muted/45 p-5 sm:p-6">
              <h2 id="shipping-snapshot-title" className="text-lg font-black text-foreground">آدرس ثبت‌شده برای سفارش</h2>
              <p className="mt-3 font-bold text-foreground">{order.shipping_recipient_first_name} {order.shipping_recipient_last_name}</p>
              <p className="mt-2 break-words text-sm leading-7 text-muted-foreground">{order.shipping_province}، {order.shipping_city}، {order.shipping_address}</p>
              <p className="mt-2 text-xs text-muted-foreground"><bdi dir="ltr">{order.shipping_recipient_phone_number}</bdi> · کد پستی <bdi>{order.shipping_postal_code}</bdi></p>
            </section>
          </div>

          <aside aria-labelledby="result-summary-title" className="rounded-xl border border-border/80 bg-surface p-5 lg:sticky lg:top-28 xl:p-6">
            <h2 id="result-summary-title" className="text-lg font-black text-foreground">مبالغ سفارش</h2>
            <dl className="mt-5 space-y-3 border-y border-border/70 py-4 text-sm">
              <div className="flex justify-between gap-4"><dt className="text-muted-foreground">جمع کالاها</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.subtotal)}</bdi></dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted-foreground">تخفیف</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.discount_total)}</bdi></dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted-foreground">هزینه ارسال</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.shipping_total)}</bdi></dd></div>
              <div className="flex items-center justify-between gap-4 border-t border-border/70 pt-3"><dt className="font-black text-foreground">مبلغ نهایی</dt><dd className="text-lg font-black tabular-nums text-primary"><bdi>{formatToman(order.grand_total)}</bdi></dd></div>
            </dl>
            {order.status === "PENDING_PAYMENT" ? <p className="mt-4 rounded-lg bg-primary-soft/55 px-3 py-3 text-xs font-semibold leading-6 text-foreground">سفارش ثبت شده اما پرداخت نشده است. پرداخت در مرحلهٔ بعدی محصول پیاده‌سازی می‌شود.</p> : null}
            <Link href="/products" className="mt-6 inline-flex min-h-12 w-full items-center justify-center rounded-lg bg-primary px-5 text-sm font-extrabold text-primary-foreground hover:bg-primary-hover">بازگشت به محصولات</Link>
          </aside>
        </div>
      </section>
    </Container>
  );
}
