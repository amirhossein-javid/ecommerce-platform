import Link from "next/link";

import { Container } from "@/components/container";

export default function ProductNotFound() {
  return (
    <Container className="py-10 sm:py-14 lg:py-20">
      <section className="mx-auto max-w-2xl rounded-2xl border border-dashed border-border bg-surface px-6 py-14 text-center shadow-card sm:px-10 sm:py-20">
        <div className="mx-auto grid size-16 place-items-center rounded-2xl border border-border bg-surface-muted text-primary" aria-hidden="true">
          <svg viewBox="0 0 48 48" fill="none" className="size-8">
            <path d="M8 15.5 24 7l16 8.5v17L24 41 8 32.5v-17Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
            <path d="m8.5 15.5 15.5 9 15.5-9M24 24.5V41" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
          </svg>
        </div>
        <h1 className="mt-6 text-2xl font-black tracking-tight text-foreground sm:text-3xl">
          این محصول پیدا نشد
        </h1>
        <p className="mx-auto mt-3 max-w-md leading-8 text-muted-foreground">
          ممکن است محصول حذف شده باشد یا دیگر در فهرست عمومی فروشگاه نمایش داده نشود.
        </p>
        <Link
          href="/products"
          className="mt-7 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
        >
          مشاهدهٔ محصولات
        </Link>
      </section>
    </Container>
  );
}
