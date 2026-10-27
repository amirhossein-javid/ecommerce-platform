import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { AccountSidebar } from "@/components/account-sidebar";
import { Container } from "@/components/container";
import { OrderStatusBadge } from "@/components/order-status-badge";
import { PaymentPanel } from "@/components/payment-panel";
import { StorefrontPageHeader } from "@/components/storefront-page-header";
import { getCustomerSession } from "@/lib/auth-session";
import { parseOrderId } from "@/lib/checkout-contract";
import { formatToman } from "@/lib/format-price";
import { getCustomerOrderDetail, OrderApiError } from "@/lib/order-api";
import { classifyOrderFailure } from "@/lib/order-policy";

export const metadata: Metadata = {
  title: "جزئیات سفارش | نقش‌جهان",
  description: "مشاهدهٔ اقلام، مبلغ، آدرس و وضعیت سفارش",
};

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") redirect("/login");
  if (session.state === "missing-profile") redirect("/account");
  const orderId = parseOrderId((await params).id);
  if (!orderId) notFound();

  if (session.state === "upstream-error") {
    return <Container className="py-10 sm:py-16"><p role="alert" className="rounded-xl bg-destructive-soft/45 px-5 py-12 text-center font-bold text-destructive">بررسی نشست مشتری ممکن نشد. کمی بعد دوباره تلاش کنید.</p></Container>;
  }

  let order;
  try {
    order = await getCustomerOrderDetail(orderId);
  } catch (error) {
    const failure = classifyOrderFailure(error instanceof OrderApiError ? error.status : undefined, error instanceof OrderApiError ? error.payload : undefined);
    if (failure === "session-expired") redirect("/login");
    if (failure === "not-found") notFound();
    return (
      <Container className="py-10 sm:py-16">
        <section role="alert" className="mx-auto max-w-2xl rounded-xl bg-destructive-soft/45 px-5 py-12 text-center">
          <h1 className="text-2xl font-black text-foreground">دریافت سفارش ممکن نشد</h1>
          <p className="mt-3 leading-8 text-muted-foreground">{failure === "rate-limited" ? "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید." : "ارتباط با سرویس سفارش‌ها برقرار نشد. کمی بعد دوباره تلاش کنید."}</p>
          <Link href={`/account/orders/${orderId}`} className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">تلاش دوباره</Link>
        </section>
      </Container>
    );
  }

  const createdAt = new Intl.DateTimeFormat("fa-IR", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(order.created_at));

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <StorefrontPageHeader
        eyebrow="جزئیات سفارش"
        title={<>سفارش شمارهٔ <bdi>{order.id.toLocaleString("fa-IR")}</bdi></>}
        description={`ثبت‌شده در ${createdAt}`}
        trailing={<div className="flex flex-wrap items-center justify-center gap-3"><OrderStatusBadge status={order.status} /><Link href="/account/orders" className="rounded-full border border-gold/50 px-4 py-2 text-xs font-bold text-white hover:bg-white/10">بازگشت به سفارش‌ها</Link></div>}
      />

      <div className="grid min-w-0 gap-7 lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start lg:gap-10">
        <AccountSidebar customer={session.customer} active="orders" />
        <div className="min-w-0 space-y-6">
          <section className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-7" aria-labelledby="order-items-title">
            <h2 id="order-items-title" className="text-xl font-black text-foreground">کالاهای سفارش</h2>
            <div className="mt-4 divide-y divide-gold/30 border-y border-gold/30">
              {order.items.map((item, index) => (
                <article key={`${item.sku}-${index}`} className="py-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><h3 className="font-extrabold text-foreground">{item.product_name}</h3><p className="mt-1 text-xs text-muted-foreground">کد کالا: <bdi>{item.sku}</bdi></p></div>
                    <strong className="tabular-nums text-primary"><bdi>{formatToman(item.line_total)}</bdi></strong>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">{item.quantity.toLocaleString("fa-IR")} عدد × <bdi>{formatToman(item.unit_price)}</bdi></p>
                </article>
              ))}
            </div>
          </section>

          <div className="grid gap-6 xl:grid-cols-2">
            <section className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-6" aria-labelledby="delivery-title">
              <h2 id="delivery-title" className="text-lg font-black text-foreground">آدرس تحویل ثبت‌شده</h2>
              {order.shipping_title ? <p className="mt-3 text-xs font-bold text-primary">{order.shipping_title}</p> : null}
              <p className="mt-2 font-bold">{order.shipping_recipient_first_name} {order.shipping_recipient_last_name}</p>
              <p className="mt-2 break-words text-sm leading-7 text-muted-foreground">{order.shipping_province}، {order.shipping_city}، {order.shipping_address}</p>
              <p className="mt-2 text-xs text-muted-foreground"><bdi dir="ltr">{order.shipping_recipient_phone_number}</bdi> · کد پستی <bdi>{order.shipping_postal_code}</bdi></p>
            </section>

            <aside className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-6" aria-labelledby="totals-title">
              <h2 id="totals-title" className="text-lg font-black text-foreground">مبالغ سفارش</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4"><dt className="text-muted-foreground">جمع کالاها</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.subtotal)}</bdi></dd></div>
                <div className="flex justify-between gap-4"><dt className="text-muted-foreground">تخفیف</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.discount_total)}</bdi></dd></div>
                <div className="flex justify-between gap-4"><dt className="text-muted-foreground">هزینهٔ ارسال</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.shipping_total)}</bdi></dd></div>
                <div className="flex justify-between gap-4 border-t border-gold/30 pt-3"><dt className="font-black">مبلغ نهایی</dt><dd className="text-lg font-black tabular-nums text-lapis"><bdi>{formatToman(order.grand_total)}</bdi></dd></div>
              </dl>
              <PaymentPanel orderId={order.id} initialOrderStatus={order.status} />
            </aside>
          </div>
        </div>
      </div>
    </Container>
  );
}
