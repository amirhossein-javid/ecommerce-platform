import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AccountSidebar } from "@/components/account-sidebar";
import { Container } from "@/components/container";
import { ProfileForm } from "@/components/profile-form";
import { StorefrontPageHeader } from "@/components/storefront-page-header";
import { getCustomerSession } from "@/lib/auth-session";

export const metadata: Metadata = {
  title: "حساب کاربری | نقش‌جهان",
  description: "مشاهده و ویرایش اطلاعات حساب مشتری",
};

function AccountServiceError() {
  return (
    <Container className="py-10 sm:py-16">
      <section className="mx-auto max-w-2xl rounded-xl bg-destructive-soft/45 px-5 py-12 text-center" role="alert">
        <h1 className="text-2xl font-black text-foreground">دریافت حساب ممکن نشد</h1>
        <p className="mt-3 leading-8 text-muted-foreground">ارتباط با سرویس حساب کاربری برقرار نشد. کمی بعد دوباره تلاش کنید.</p>
        <Link href="/account" className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">تلاش دوباره</Link>
      </section>
    </Container>
  );
}

function MissingCustomerProfile() {
  return (
    <Container className="py-10 sm:py-16">
      <section className="mx-auto max-w-2xl rounded-xl border border-border/75 bg-surface px-5 py-12 text-center sm:px-8">
        <div className="mx-auto grid size-14 place-items-center rounded-xl bg-primary-soft text-2xl font-black text-primary" aria-hidden="true">!</div>
        <h1 className="mt-5 text-2xl font-black text-foreground">پروفایل مشتری برای این حساب وجود ندارد</h1>
        <p className="mx-auto mt-3 max-w-lg leading-8 text-muted-foreground">این شناسه وارد شده است، اما حساب مشتری فروشگاه نیست. از گزینهٔ خروج در بالای صفحه استفاده کنید و با حساب مشتری وارد شوید.</p>
      </section>
    </Container>
  );
}

export default async function AccountPage() {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") redirect("/login");
  if (session.state === "missing-profile") return <MissingCustomerProfile />;
  if (session.state === "upstream-error") return <AccountServiceError />;
  const customer = session.customer;

  const displayName = [customer.first_name, customer.last_name]
    .filter(Boolean)
    .join(" ") || "مشتری فروشگاه";
  const joinedAt = new Intl.DateTimeFormat("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(customer.created_at));

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <StorefrontPageHeader eyebrow="حساب مشتری" title={<>سلام، {displayName}</>} description="اطلاعات حساب و راه‌های ارتباطی خود را مشاهده و ویرایش کنید." />

      <div className="grid min-w-0 gap-7 lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start lg:gap-10">
        <AccountSidebar customer={customer} active="profile" />

        <section className="min-w-0 rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-7 lg:p-8" aria-labelledby="profile-title">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-gold/30 pb-5">
            <div>
              <h2 id="profile-title" className="text-xl font-black text-foreground sm:text-2xl">اطلاعات شخصی</h2>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">این اطلاعات برای ارتباط با شما استفاده می‌شود.</p>
            </div>
            <p className="text-xs text-muted-foreground">عضویت از {joinedAt}</p>
          </div>
          <ProfileForm profile={customer} />
        </section>
      </div>
    </Container>
  );
}
