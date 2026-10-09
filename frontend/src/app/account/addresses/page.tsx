import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AccountSidebar } from "@/components/account-sidebar";
import { AddressManager } from "@/components/address-manager";
import { Container } from "@/components/container";
import { getCustomerSession } from "@/lib/auth-session";

export const metadata: Metadata = {
  title: "آدرس‌های من | فروشگاه",
  description: "مدیریت آدرس‌های مشتری فروشگاه",
};

export default async function AddressesPage() {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") redirect("/login");

  if (session.state === "missing-profile") {
    return (
      <Container className="py-10 sm:py-16">
        <section className="mx-auto max-w-2xl rounded-xl border border-border/75 bg-surface px-5 py-12 text-center">
          <h1 className="text-2xl font-black text-foreground">پروفایل مشتری برای این حساب وجود ندارد</h1>
          <p className="mt-3 leading-8 text-muted-foreground">برای مدیریت آدرس‌ها با یک حساب مشتری وارد شوید.</p>
        </section>
      </Container>
    );
  }

  if (session.state === "upstream-error") {
    return (
      <Container className="py-10 sm:py-16">
        <section className="mx-auto max-w-2xl rounded-xl bg-destructive-soft/45 px-5 py-12 text-center" role="alert">
          <h1 className="text-2xl font-black text-foreground">دریافت حساب ممکن نشد</h1>
          <p className="mt-3 leading-8 text-muted-foreground">ارتباط با سرویس حساب کاربری برقرار نشد. کمی بعد دوباره تلاش کنید.</p>
          <Link href="/account/addresses" className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">تلاش دوباره</Link>
        </section>
      </Container>
    );
  }

  return (
    <Container className="py-7 sm:py-10 lg:py-14">
      <header className="mb-7 border-b border-border/75 pb-6 sm:mb-9">
        <p className="text-sm font-bold text-primary">حساب مشتری</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-foreground sm:text-4xl">مدیریت آدرس‌ها</h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground sm:text-base">آدرس‌های دریافت سفارش را ثبت و به‌روزرسانی کنید.</p>
      </header>

      <div className="grid min-w-0 gap-7 lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start lg:gap-10">
        <AccountSidebar customer={session.customer} active="addresses" />
        <section className="min-w-0 rounded-xl border border-border/75 bg-surface p-5 sm:p-7 lg:p-8">
          <AddressManager />
        </section>
      </div>
    </Container>
  );
}
