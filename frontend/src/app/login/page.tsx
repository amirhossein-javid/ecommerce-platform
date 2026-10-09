import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { Container } from "@/components/container";
import { getCurrentCustomer } from "@/lib/auth-session";

export const metadata: Metadata = {
  title: "ورود | فروشگاه",
  description: "ورود امن به حساب کاربری فروشگاه",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string }>;
}) {
  if (await getCurrentCustomer()) redirect("/");
  const { registered } = await searchParams;

  return (
    <Container className="py-10 sm:py-16">
      <section className="mx-auto max-w-md rounded-xl border border-border/80 bg-surface p-5 shadow-card sm:p-8" aria-labelledby="login-title">
        <p className="text-sm font-bold text-primary">حساب کاربری</p>
        <h1 id="login-title" className="mt-2 text-2xl font-black tracking-tight text-foreground sm:text-3xl">ورود به فروشگاه</h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">برای ادامه، ایمیل و رمز عبور خود را وارد کنید.</p>
        <AuthForm mode="login" registered={registered === "1"} />
      </section>
    </Container>
  );
}
