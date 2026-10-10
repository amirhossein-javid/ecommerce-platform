import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { Container } from "@/components/container";
import { getCurrentCustomer } from "@/lib/auth-session";

export const metadata: Metadata = {
  title: "ورود | نقش‌جهان",
  description: "ورود به حساب کاربری فروشگاه نقش‌جهان",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string }>;
}) {
  if (await getCurrentCustomer()) redirect("/");
  const { registered } = await searchParams;

  return (
    <Container className="py-7 sm:py-12 lg:py-16">
      <section className="mx-auto grid max-w-5xl overflow-hidden rounded-[1.5rem] border border-gold/40 bg-surface shadow-card lg:grid-cols-[0.9fr_1.1fr]" aria-labelledby="login-title">
        <div className="naghsh-pattern relative isolate flex min-h-56 flex-col justify-end p-6 text-white sm:p-9 lg:min-h-[36rem]">
          <div className="absolute inset-0 -z-10 bg-lapis-dark/82" />
          <p className="text-xs font-black text-gold-light">حساب نقش‌جهان</p>
          <h2 className="mt-3 text-2xl font-black leading-10 sm:text-3xl">مسیر خریدتان را از همان‌جا ادامه دهید</h2>
          <p className="mt-3 text-sm leading-8 text-white/72">پس از ورود، سبد خرید مهمان با حساب شما ادغام می‌شود و سفارش‌ها و آدرس‌های متعلق به حسابتان در دسترس خواهند بود.</p>
        </div>
        <div className="p-5 sm:p-9 lg:p-11">
          <p className="flex items-center gap-2 text-xs font-black text-primary"><span className="size-1.5 rotate-45 bg-gold" aria-hidden="true" /> حساب کاربری</p>
          <h1 id="login-title" className="mt-3 text-2xl font-black tracking-tight text-foreground sm:text-3xl">ورود به فروشگاه</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">برای ادامه، ایمیل و رمز عبور خود را وارد کنید.</p>
          <AuthForm mode="login" registered={registered === "1"} />
        </div>
      </section>
    </Container>
  );
}
