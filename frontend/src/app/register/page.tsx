import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { Container } from "@/components/container";
import { getCurrentCustomer } from "@/lib/auth-session";

export const metadata: Metadata = {
  title: "ثبت‌نام | نقش‌جهان",
  description: "ساخت حساب مشتری در فروشگاه نقش‌جهان",
};

export default async function RegisterPage() {
  if (await getCurrentCustomer()) redirect("/");

  return (
    <Container className="py-7 sm:py-12 lg:py-16">
      <section className="mx-auto grid max-w-6xl overflow-hidden rounded-[1.5rem] border border-gold/40 bg-surface shadow-card lg:grid-cols-[0.82fr_1.18fr]" aria-labelledby="register-title">
        <div className="naghsh-pattern relative isolate flex min-h-56 flex-col justify-end p-6 text-white sm:p-9 lg:min-h-[43rem]">
          <div className="absolute inset-0 -z-10 bg-lapis-dark/82" />
          <p className="text-xs font-black text-gold-light">عضویت در نقش‌جهان</p>
          <h2 className="mt-3 text-2xl font-black leading-10 sm:text-3xl">حسابی برای خرید و پیگیری سفارش‌ها</h2>
          <p className="mt-3 text-sm leading-8 text-white/72">اطلاعات حساب برای ورود، مدیریت آدرس‌ها و دسترسی به سفارش‌های خودتان استفاده می‌شود.</p>
        </div>
        <div className="p-5 sm:p-9 lg:p-11">
          <p className="flex items-center gap-2 text-xs font-black text-primary"><span className="size-1.5 rotate-45 bg-gold" aria-hidden="true" /> حساب جدید</p>
          <h1 id="register-title" className="mt-3 text-2xl font-black tracking-tight text-foreground sm:text-3xl">ثبت‌نام در فروشگاه</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">اطلاعات واقعی خود را وارد کنید؛ پس از ثبت‌نام به صفحهٔ ورود هدایت می‌شوید.</p>
          <AuthForm mode="register" />
        </div>
      </section>
    </Container>
  );
}
