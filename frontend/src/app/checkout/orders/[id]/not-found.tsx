import Link from "next/link";

import { Container } from "@/components/container";

export default function OrderNotFound() {
  return (
    <Container className="py-10 sm:py-16">
      <section className="mx-auto max-w-2xl rounded-[1.5rem] border border-gold/40 bg-surface px-5 py-14 text-center shadow-card sm:px-8">
        <h1 className="text-2xl font-black text-foreground">سفارش پیدا نشد</h1>
        <p className="mt-3 leading-8 text-muted-foreground">این سفارش وجود ندارد یا به حساب شما تعلق ندارد.</p>
        <Link href="/products" className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">مشاهدهٔ محصولات</Link>
      </section>
    </Container>
  );
}
