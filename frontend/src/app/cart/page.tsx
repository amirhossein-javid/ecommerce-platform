import type { Metadata } from "next";
import Link from "next/link";

import { CartView } from "@/components/cart-view";
import { Container } from "@/components/container";
import { getCustomerSession } from "@/lib/auth-session";
import { getCurrentCart } from "@/lib/cart-api";

export const metadata: Metadata = {
  title: "سبد خرید | نقش‌جهان",
  description: "مشاهده و مدیریت سبد خرید نقش‌جهان",
};

function CartError() {
  return (
    <section
      role="alert"
      className="rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-5 py-14 text-center sm:px-8"
    >
      <div
        className="mx-auto grid size-14 place-items-center rounded-full border border-destructive/25 bg-surface text-2xl font-black text-destructive"
        aria-hidden="true"
      >
        !
      </div>
      <h2 className="mt-5 text-xl font-black text-foreground">
        دریافت سبد خرید ممکن نشد
      </h2>
      <p className="mx-auto mt-3 max-w-lg leading-8 text-muted-foreground">
        ارتباط با سرویس فروشگاه برقرار نشد. لطفاً کمی بعد دوباره تلاش کنید.
      </p>
      <Link
        href="/cart"
        className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
      >
        تلاش دوباره
      </Link>
    </section>
  );
}

type CartPageProps = {
  searchParams: Promise<{ merge?: string | string[] }>;
};

export default async function CartPage({ searchParams }: CartPageProps) {
  let cart;
  const session = await getCustomerSession();

  try {
    cart = await getCurrentCart();
  } catch {
    return (
      <Container className="py-6 sm:py-9 lg:py-12">
        <CartError />
      </Container>
    );
  }

  const rawMerge = (await searchParams).merge;
  const initialMergeState =
    typeof rawMerge === "string" &&
    ["pending", "unavailable"].includes(rawMerge)
      ? (rawMerge as "pending" | "unavailable")
      : undefined;

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <header className="naghsh-pattern relative isolate mb-7 overflow-hidden rounded-[1.5rem] px-5 py-10 text-center text-white sm:mb-9 sm:px-10 sm:py-12">
        <div className="absolute inset-0 -z-10 bg-lapis-dark/82" />
        <p className="flex items-center justify-center gap-3 text-xs font-black text-gold-light sm:text-sm"><span className="size-2 rotate-45 bg-gold" aria-hidden="true" />خرید شما<span className="size-2 rotate-45 bg-gold" aria-hidden="true" /></p>
        <h1 className="mt-3 text-3xl font-black tracking-tight text-white sm:text-4xl">
          سبد خرید
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-white/72 sm:text-base">
          تعداد کالاها، وضعیت موجودی و جمع قیمت را پیش از ادامه مرور کنید.
        </p>
      </header>
      <CartView
        initialCart={cart}
        initialMergeState={initialMergeState}
        checkoutState={
          session.state === "customer"
            ? "customer"
            : session.state === "guest" || session.state === "invalid"
              ? "guest"
              : "blocked"
        }
      />
    </Container>
  );
}
