import type { Metadata } from "next";
import Link from "next/link";

import { CartView } from "@/components/cart-view";
import { Container } from "@/components/container";
import { getCustomerSession } from "@/lib/auth-session";
import { getCurrentCart } from "@/lib/cart-api";

export const metadata: Metadata = {
  title: "سبد خرید | فروشگاه",
  description: "مشاهده و مدیریت سبد خرید",
};

function CartError() {
  return (
    <section
      role="alert"
      className="rounded-xl bg-destructive-soft/45 px-5 py-14 text-center sm:px-8"
    >
      <div
        className="mx-auto grid size-14 place-items-center rounded-xl bg-destructive-soft text-2xl font-black text-destructive"
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
        className="mt-7 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
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
      <Container className="py-7 sm:py-10 lg:py-14">
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
    <Container className="py-7 sm:py-10 lg:py-14">
      <header className="mb-7 border-b border-border/75 pb-6 sm:mb-9">
        <p className="text-sm font-bold text-primary">خرید شما</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-foreground sm:text-4xl">
          سبد خرید
        </h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground sm:text-base">
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
