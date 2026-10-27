import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AccountSidebar } from "@/components/account-sidebar";
import { Container } from "@/components/container";
import { OrderStatusBadge } from "@/components/order-status-badge";
import { StorefrontPageHeader } from "@/components/storefront-page-header";
import { getCustomerSession } from "@/lib/auth-session";
import { formatToman } from "@/lib/format-price";
import { getCustomerOrders, OrderApiError } from "@/lib/order-api";
import { parseOrderPage } from "@/lib/order-contract";
import { classifyOrderFailure } from "@/lib/order-policy";

export const metadata: Metadata = {
  title: "سفارش‌های من | نقش‌جهان",
  description: "مشاهدهٔ تاریخچه و وضعیت سفارش‌های مشتری",
};

type OrdersPageProps = {
  searchParams: Promise<{ page?: string | string[] }>;
};

function pageHref(page: number) {
  return page === 1 ? "/account/orders" : `/account/orders?page=${page}`;
}

function OrdersError({ page, message }: { page: number; message: string }) {
  return (
    <section className="rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-5 py-12 text-center" role="alert">
      <h2 className="text-xl font-black text-foreground">دریافت سفارش‌ها ممکن نشد</h2>
      <p className="mt-3 leading-8 text-muted-foreground">{message}</p>
      <Link href={pageHref(page)} className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">تلاش دوباره</Link>
    </section>
  );
}

export default async function OrdersPage({ searchParams }: OrdersPageProps) {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") redirect("/login");
  if (session.state === "missing-profile") redirect("/account");
  if (session.state === "upstream-error") {
    return <Container className="py-10 sm:py-16"><OrdersError page={1} message="ارتباط با سرویس حساب کاربری برقرار نشد. کمی بعد دوباره تلاش کنید." /></Container>;
  }

  const page = parseOrderPage((await searchParams).page);
  let orders;
  try {
    orders = await getCustomerOrders(page);
  } catch (error) {
    const failure = classifyOrderFailure(
      error instanceof OrderApiError ? error.status : undefined,
      error instanceof OrderApiError ? error.payload : undefined,
    );
    if (failure === "session-expired") redirect("/login");
    const message = failure === "rate-limited"
      ? "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید."
      : failure === "missing-profile"
        ? "این حساب پروفایل مشتری فروشگاه ندارد."
        : "ارتباط با سرویس سفارش‌ها برقرار نشد. کمی بعد دوباره تلاش کنید.";
    return <Container className="py-10 sm:py-16"><OrdersError page={page} message={message} /></Container>;
  }

  const totalPages = Math.max(1, Math.ceil(orders.count / 20));

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <StorefrontPageHeader eyebrow="حساب مشتری" title="سفارش‌های من" description="تاریخچه، مبلغ نهایی و وضعیت واقعی سفارش‌های خود را ببینید." />

      <div className="grid min-w-0 gap-7 lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start lg:gap-10">
        <AccountSidebar customer={session.customer} active="orders" />
        <div className="min-w-0">
          {orders.count === 0 ? (
            <section className="rounded-[1.5rem] border border-gold/40 bg-surface px-5 py-14 text-center shadow-card sm:px-8">
              <div className="mx-auto grid size-14 place-items-center rounded-full border-2 border-gold bg-background text-2xl text-primary" aria-hidden="true">□</div>
              <h2 className="mt-5 text-2xl font-black text-foreground">هنوز سفارشی ندارید</h2>
              <p className="mt-3 leading-8 text-muted-foreground">پس از ثبت سفارش، وضعیت و جزئیات آن در این صفحه نمایش داده می‌شود.</p>
              <Link href="/products" className="mt-6 inline-flex min-h-12 items-center rounded-full bg-primary px-6 text-sm font-extrabold text-primary-foreground hover:bg-primary-hover">مشاهدهٔ محصولات</Link>
            </section>
          ) : (
            <>
              <div className="space-y-4">
                {orders.results.map((order) => {
                  const date = new Intl.DateTimeFormat("fa-IR", { year: "numeric", month: "long", day: "numeric" }).format(new Date(order.created_at));
                  const quantity = order.items.reduce((sum, item) => sum + item.quantity, 0);
                  const firstNames = order.items.slice(0, 2).map((item) => item.product_name).join("، ");
                  const remaining = order.items.length - 2;
                  return (
                    <article key={order.id} className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card transition motion-safe:hover:-translate-y-0.5 hover:border-gold/70 sm:p-6">
                      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-gold/30 pb-4">
                        <div>
                          <p className="text-xs font-bold text-muted-foreground">سفارش شمارهٔ <bdi>{order.id.toLocaleString("fa-IR")}</bdi></p>
                          <time dateTime={order.created_at} className="mt-1 block text-sm font-semibold text-foreground">{date}</time>
                        </div>
                        <OrderStatusBadge status={order.status} />
                      </div>
                      <div className="mt-4 grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-bold text-foreground">{firstNames}{remaining > 0 ? ` و ${remaining.toLocaleString("fa-IR")} کالای دیگر` : ""}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{quantity.toLocaleString("fa-IR")} عدد کالا</p>
                        </div>
                        <div className="sm:text-end">
                          <p className="text-xs text-muted-foreground">مبلغ نهایی</p>
                          <strong className="mt-1 block tabular-nums text-primary"><bdi>{formatToman(order.grand_total)}</bdi></strong>
                        </div>
                      </div>
                      <Link href={`/account/orders/${order.id}`} className="mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-full border border-primary/30 px-5 text-sm font-extrabold text-primary hover:bg-primary-soft/50 sm:w-auto">مشاهدهٔ جزئیات سفارش</Link>
                    </article>
                  );
                })}
              </div>
              {totalPages > 1 ? (
                <nav aria-label="صفحه‌بندی سفارش‌ها" className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-gold/35 pt-6">
                  {page > 1 ? <Link rel="prev" href={pageHref(page - 1)} className="inline-flex min-h-11 items-center rounded-full border border-gold/35 bg-surface px-4 text-sm font-bold hover:bg-primary-soft hover:text-primary">→ صفحهٔ قبل</Link> : <span />}
                  <p className="text-sm font-bold text-muted-foreground">صفحهٔ {page.toLocaleString("fa-IR")} از {totalPages.toLocaleString("fa-IR")}</p>
                  {page < totalPages ? <Link rel="next" href={pageHref(page + 1)} className="inline-flex min-h-11 items-center rounded-full border border-gold/35 bg-surface px-4 text-sm font-bold hover:bg-primary-soft hover:text-primary">صفحهٔ بعد ←</Link> : <span />}
                </nav>
              ) : null}
            </>
          )}
        </div>
      </div>
    </Container>
  );
}
