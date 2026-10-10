import Link from "next/link";

import { Container } from "@/components/container";

export default function OrderNotFound() {
  return (
    <Container className="py-12 sm:py-20">
      <section className="mx-auto max-w-2xl rounded-[1.5rem] border border-gold/40 bg-surface px-5 py-14 text-center shadow-card">
        <h1 className="text-2xl font-black text-foreground">سفارش پیدا نشد</h1>
        <p className="mt-3 leading-8 text-muted-foreground">این سفارش وجود ندارد یا به حساب شما تعلق ندارد.</p>
        <Link href="/account/orders" className="mt-6 inline-flex min-h-12 items-center rounded-full bg-primary px-6 text-sm font-extrabold text-primary-foreground hover:bg-primary-hover">بازگشت به سفارش‌های من</Link>
      </section>
    </Container>
  );
}
