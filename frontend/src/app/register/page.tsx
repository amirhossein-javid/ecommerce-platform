import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { Container } from "@/components/container";
import { getCurrentCustomer } from "@/lib/auth-session";

export const metadata: Metadata = {
  title: "ثبت‌نام | فروشگاه",
  description: "ساخت حساب مشتری در فروشگاه",
};

export default async function RegisterPage() {
  if (await getCurrentCustomer()) redirect("/");

  return (
    <Container className="py-10 sm:py-16">
      <section className="mx-auto max-w-xl rounded-xl border border-border/80 bg-surface p-5 shadow-card sm:p-8" aria-labelledby="register-title">
        <p className="text-sm font-bold text-primary">حساب جدید</p>
        <h1 id="register-title" className="mt-2 text-2xl font-black tracking-tight text-foreground sm:text-3xl">ثبت‌نام در فروشگاه</h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">اطلاعات واقعی خود را وارد کنید؛ پس از ثبت‌نام به صفحهٔ ورود هدایت می‌شوید.</p>
        <AuthForm mode="register" />
      </section>
    </Container>
  );
}
