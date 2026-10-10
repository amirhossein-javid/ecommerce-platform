import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Container } from "@/components/container";
import { PaymentPanel } from "@/components/payment-panel";
import { OrderStatusBadge } from "@/components/order-status-badge";
import { StorefrontPageHeader } from "@/components/storefront-page-header";
import { getCustomerSession } from "@/lib/auth-session";
import { CheckoutApiError, getCustomerOrder } from "@/lib/checkout-api";
import { parseOrderId } from "@/lib/checkout-contract";
import { formatToman } from "@/lib/format-price";

export const metadata: Metadata = {
  title: "نتیجهٔ ثبت سفارش | نقش‌جهان",
  description: "مشاهدهٔ نتیجه و وضعیت واقعی سفارش",
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
        <section role="alert" className="mx-auto max-w-2xl rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-5 py-12 text-center">
          <h1 className="text-2xl font-black text-foreground">دریافت وضعیت سفارش ممکن نشد</h1>
          <p className="mt-3 leading-8 text-muted-foreground">ارتباط با سرویس سفارش‌ها برقرار نشد. کمی بعد دوباره تلاش کنید.</p>
          <Link href={`/checkout/orders/${orderId}`} className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">تلاش دوباره</Link>
        </section>
      </Container>
    );
  }

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <section className="mx-auto max-w-5xl">
        <StorefrontPageHeader
          eyebrow="سفارش ثبت شد"
          title={<>سفارش شمارهٔ <bdi>{order.id.toLocaleString("fa-IR")}</bdi></>}
          description={order.status === "PENDING_PAYMENT" ? "سفارش ثبت شده است و پرداخت هنوز تأیید نشده است." : "وضعیت فعلی سفارش مستقیماً از فروشگاه دریافت شده است."}
          trailing={<OrderStatusBadge status={order.status} />}
        />

        <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start xl:gap-10">
          <div className="min-w-0 space-y-8">
            <section aria-labelledby="result-items-title" className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-6">
              <h2 id="result-items-title" className="border-b border-gold/30 pb-4 text-xl font-black text-foreground">کالاهای سفارش</h2>
              <div className="divide-y divide-gold/30">
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

            <section aria-labelledby="shipping-snapshot-title" className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-6">
              <h2 id="shipping-snapshot-title" className="text-lg font-black text-foreground">آدرس ثبت‌شده برای سفارش</h2>
              <p className="mt-3 font-bold text-foreground">{order.shipping_recipient_first_name} {order.shipping_recipient_last_name}</p>
              <p className="mt-2 break-words text-sm leading-7 text-muted-foreground">{order.shipping_province}، {order.shipping_city}، {order.shipping_address}</p>
              <p className="mt-2 text-xs text-muted-foreground"><bdi dir="ltr">{order.shipping_recipient_phone_number}</bdi> · کد پستی <bdi>{order.shipping_postal_code}</bdi></p>
            </section>
          </div>

          <aside aria-labelledby="result-summary-title" className="rounded-[1.5rem] border border-gold/45 bg-surface p-5 shadow-card lg:sticky lg:top-28 xl:p-6">
            <h2 id="result-summary-title" className="text-lg font-black text-foreground">مبالغ سفارش</h2>
            <dl className="mt-5 space-y-3 rounded-[1.1rem] bg-background px-4 py-5 text-sm">
              <div className="flex justify-between gap-4"><dt className="text-muted-foreground">جمع کالاها</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.subtotal)}</bdi></dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted-foreground">تخفیف</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.discount_total)}</bdi></dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted-foreground">هزینه ارسال</dt><dd className="font-bold tabular-nums"><bdi>{formatToman(order.shipping_total)}</bdi></dd></div>
              <div className="flex items-center justify-between gap-4 border-t border-gold/30 pt-3"><dt className="font-black text-foreground">مبلغ نهایی</dt><dd className="text-lg font-black tabular-nums text-lapis"><bdi>{formatToman(order.grand_total)}</bdi></dd></div>
            </dl>
            <PaymentPanel
              orderId={order.id}
              initialOrderStatus={order.status}
            />
            <Link href={`/account/orders/${order.id}`} className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-full border border-primary/30 px-5 text-sm font-bold text-primary hover:bg-primary-soft/50">مشاهده در سفارش‌های من</Link>
            <Link href="/products" className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-full px-5 text-sm font-bold text-muted-foreground hover:bg-background hover:text-primary">بازگشت به محصولات</Link>
          </aside>
        </div>
      </section>
    </Container>
  );
}
