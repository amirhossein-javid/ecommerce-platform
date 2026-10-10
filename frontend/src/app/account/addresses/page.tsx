import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AccountSidebar } from "@/components/account-sidebar";
import { AddressManager } from "@/components/address-manager";
import { Container } from "@/components/container";
import { StorefrontPageHeader } from "@/components/storefront-page-header";
import { getCustomerSession } from "@/lib/auth-session";

export const metadata: Metadata = {
  title: "آدرس‌های من | نقش‌جهان",
  description: "مدیریت آدرس‌های مشتری فروشگاه",
};

export default async function AddressesPage() {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") redirect("/login");

  if (session.state === "missing-profile") {
    return (
      <Container className="py-10 sm:py-16">
        <section className="mx-auto max-w-2xl rounded-[1.5rem] border border-gold/40 bg-surface px-5 py-12 text-center shadow-card">
          <h1 className="text-2xl font-black text-foreground">پروفایل مشتری برای این حساب وجود ندارد</h1>
          <p className="mt-3 leading-8 text-muted-foreground">برای مدیریت آدرس‌ها با یک حساب مشتری وارد شوید.</p>
        </section>
      </Container>
    );
  }

  if (session.state === "upstream-error") {
    return (
      <Container className="py-10 sm:py-16">
        <section className="mx-auto max-w-2xl rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-5 py-12 text-center" role="alert">
          <h1 className="text-2xl font-black text-foreground">دریافت حساب ممکن نشد</h1>
          <p className="mt-3 leading-8 text-muted-foreground">ارتباط با سرویس حساب کاربری برقرار نشد. کمی بعد دوباره تلاش کنید.</p>
          <Link href="/account/addresses" className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">تلاش دوباره</Link>
        </section>
      </Container>
    );
  }

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <StorefrontPageHeader eyebrow="حساب مشتری" title="مدیریت آدرس‌ها" description="آدرس‌های دریافت سفارش را ثبت و به‌روزرسانی کنید." />

      <div className="grid min-w-0 gap-7 lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start lg:gap-10">
        <AccountSidebar customer={session.customer} active="addresses" />
        <section className="min-w-0 rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-7 lg:p-8">
          <AddressManager />
        </section>
      </div>
    </Container>
  );
}
