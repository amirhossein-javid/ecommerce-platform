"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  type Cart,
  type CartItem,
  getCartItemCount,
  isCart,
  MAX_CART_QUANTITY,
} from "@/lib/cart-contract";
import { formatToman } from "@/lib/format-price";

type CartViewProps = {
  initialCart: Cart;
  initialMergeState?: "pending" | "unavailable";
  checkoutState: "customer" | "guest" | "blocked";
};

function CartImagePlaceholder() {
  return (
    <div className="grid size-full place-items-center bg-surface-muted/65 text-muted-foreground">
      <svg
        aria-hidden="true"
        viewBox="0 0 48 48"
        fill="none"
        className="size-10"
      >
        <path
          d="M8 15.5 24 7l16 8.5v17L24 41 8 32.5v-17Z"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinejoin="round"
        />
        <path
          d="m8.5 15.5 15.5 9 15.5-9M24 24.5V41"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function availabilityMessage(item: CartItem) {
  if (item.availability_reason === "insufficient_stock") {
    return "تعداد این محصول از موجودی فعلی بیشتر است؛ آن را حذف کنید و دوباره بیفزایید.";
  }
  return "این محصول دیگر برای سفارش در دسترس نیست و باید از سبد حذف شود.";
}

async function responseError(response: Response) {
  try {
    const payload = (await response.json()) as { error?: unknown };
    return typeof payload.error === "string"
      ? payload.error
      : "به‌روزرسانی سبد خرید ممکن نشد.";
  } catch {
    return "به‌روزرسانی سبد خرید ممکن نشد.";
  }
}

export function CartView({
  initialCart,
  initialMergeState,
  checkoutState,
}: CartViewProps) {
  const router = useRouter();
  const [cart, setCart] = useState(initialCart);
  const [pendingItem, setPendingItem] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [mergeState, setMergeState] = useState<
    "merged" | "pending" | "unavailable" | undefined
  >(initialMergeState);
  const [mergePending, setMergePending] = useState(false);

  const retryMerge = async () => {
    if (mergePending) return;
    setMergePending(true);
    setError("");
    try {
      const response = await fetch("/api/cart/merge", { method: "POST" });
      if (response.status === 401) {
        router.push("/login");
        router.refresh();
        return;
      }
      if (!response.ok) {
        setError(await responseError(response));
        setMergeState(response.status === 409 ? "unavailable" : "pending");
        return;
      }
      const payload: unknown = await response.json();
      if (!isCart(payload)) {
        setError("پاسخ ادغام سبد خرید معتبر نبود. صفحه را تازه کنید.");
        return;
      }
      setCart(payload);
      setMergeState("merged");
      router.replace("/cart");
      router.refresh();
    } catch {
      setError("ارتباط با سرویس سبد خرید برقرار نشد. دوباره تلاش کنید.");
      setMergeState("pending");
    } finally {
      setMergePending(false);
    }
  };

  const mergeNotice = mergeState ? (
    <div
      className={`mb-5 rounded-[1.25rem] border px-4 py-3 text-sm leading-7 ${
        mergeState === "merged"
          ? "border-success/20 bg-success-soft font-bold text-success"
          : mergeState === "pending"
            ? "border-primary/15 bg-primary-soft/70 text-foreground"
            : "border-destructive/20 bg-destructive-soft/60 text-destructive"
      }`}
      role={mergeState === "merged" ? "status" : "alert"}
    >
      {mergeState === "merged" ? (
        "کالاهای سبد مهمان با حساب شما ادغام شدند."
      ) : mergeState === "pending" ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>ورود انجام شد، اما ادغام سبد مهمان موقتاً کامل نشد. کالاها محفوظ‌اند.</span>
          <button
            type="button"
            onClick={retryMerge}
            disabled={mergePending}
            className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-full bg-primary px-4 text-xs font-bold text-primary-foreground hover:bg-primary-hover disabled:opacity-60"
          >
            {mergePending ? "در حال تلاش…" : "تلاش دوباره"}
          </button>
        </div>
      ) : (
        "سبد مهمان قبلاً مصرف شده یا دیگر در دسترس نیست. محتوای سبد فعلی حساب را بررسی کنید."
      )}
    </div>
  ) : null;

  const mutateItem = async (itemId: number, init: RequestInit) => {
    setPendingItem(itemId);
    setError("");

    try {
      const response = await fetch(`/api/cart/items/${itemId}`, init);

      if (!response.ok) {
        setError(await responseError(response));
        return;
      }

      const payload: unknown = await response.json();

      if (!isCart(payload)) {
        setError("پاسخ سبد خرید معتبر نبود. صفحه را تازه کنید.");
        return;
      }

      setCart(payload);
      router.refresh();
    } catch {
      setError("ارتباط با سبد خرید برقرار نشد. دوباره تلاش کنید.");
    } finally {
      setPendingItem(null);
    }
  };

  const updateQuantity = (item: CartItem, quantity: number) =>
    mutateItem(item.id, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity }),
    });

  const removeItem = (item: CartItem) =>
    mutateItem(item.id, { method: "DELETE" });

  if (cart.items.length === 0) {
    return (
      <>
        {mergeNotice}
        {error ? (
          <p
            role="alert"
            className="mb-5 rounded-[1.25rem] border border-destructive/20 bg-destructive-soft px-4 py-3 text-sm font-semibold text-destructive"
          >
            {error}
          </p>
        ) : null}
        <section className="rounded-[1.5rem] border border-gold/40 bg-surface px-5 py-14 text-center shadow-card sm:px-8 sm:py-20">
          <div className="mx-auto grid size-16 place-items-center rounded-full border-2 border-gold bg-background text-primary">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              className="size-8"
            >
              <path
                d="M4 5h2l1.5 9h9.75l1.5-6H7M10 18.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm8 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h2 className="mt-5 text-xl font-black text-foreground sm:text-2xl">
            سبد خرید شما خالی است
          </h2>
          <p className="mx-auto mt-3 max-w-md leading-8 text-muted-foreground">
            محصولات فروشگاه را ببینید و موارد دلخواهتان را به سبد اضافه کنید.
          </p>
          <Link
            href="/products"
            className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
          >
            مشاهدهٔ محصولات
          </Link>
        </section>
      </>
    );
  }

  const itemCount = getCartItemCount(cart);
  const hasUnavailableItems = cart.items.some((item) => !item.is_available);
  const mutationPending = pendingItem !== null;

  return (
    <>
      {mergeNotice}
      <div className="mb-5 min-h-7" aria-live="polite">
        {error ? (
          <p
            role="alert"
            className="rounded-[1.25rem] border border-destructive/20 bg-destructive-soft px-4 py-3 text-sm font-semibold text-destructive"
          >
            {error}
          </p>
        ) : null}
      </div>

      <div className="grid min-w-0 gap-7 lg:grid-cols-[minmax(0,1fr)_21rem] lg:items-start xl:gap-10">
        <section aria-labelledby="cart-items-title" className="min-w-0">
          <div className="mb-4 flex items-center justify-between gap-4 border-b border-gold/35 pb-4">
            <h2
              id="cart-items-title"
              className="text-lg font-black text-foreground"
            >
              کالاهای سبد
            </h2>
            <p className="text-sm text-muted-foreground">
              {itemCount.toLocaleString("fa-IR")} کالا
            </p>
          </div>

          <div className="space-y-4">
            {cart.items.map((item) => {
              const pending = pendingItem === item.id;
              const image = item.product.primary_image;

              return (
                <article
                  key={item.id}
                  aria-busy={pending}
                  className="grid min-w-0 grid-cols-[5.5rem_minmax(0,1fr)] gap-4 rounded-[1.25rem] border border-gold/35 bg-surface p-4 shadow-card sm:grid-cols-[8rem_minmax(0,1fr)] sm:gap-6 sm:p-5"
                >
                  <Link
                    href={`/products/${item.product.slug}`}
                    className="aspect-square overflow-hidden rounded-[1rem] border border-gold/35 bg-background"
                    aria-label={`مشاهدهٔ ${item.product.name}`}
                  >
                    {image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={image.image}
                        alt={image.alt_text || item.product.name}
                        className="size-full object-contain p-2 transition-transform duration-500 hover:scale-105"
                      />
                    ) : (
                      <CartImagePlaceholder />
                    )}
                  </Link>

                  <div className="flex min-w-0 flex-col">
                    <Link
                      href={`/products/${item.product.slug}`}
                      className="line-clamp-2 text-sm font-extrabold leading-7 text-foreground transition-colors hover:text-primary sm:text-base sm:leading-8"
                    >
                      {item.product.name}
                    </Link>

                    <p className="mt-2 text-xs text-muted-foreground sm:text-sm">
                      قیمت واحد: <bdi>{formatToman(item.product.price)}</bdi>
                    </p>

                    {!item.is_available ? (
                      <p className="mt-3 rounded-xl border border-destructive/15 bg-destructive-soft/65 px-3 py-2 text-xs font-semibold leading-6 text-destructive">
                        {availabilityMessage(item)}
                      </p>
                    ) : null}

                    <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
                      <div>
                        <p className="mb-1.5 text-xs font-semibold text-muted-foreground">
                          تعداد
                        </p>
                        <div className="inline-flex min-h-11 items-center overflow-hidden rounded-full border border-gold/45 bg-background">
                          <button
                            type="button"
                            onClick={() =>
                              updateQuantity(item, item.quantity + 1)
                            }
                            disabled={
                              mutationPending ||
                              !item.is_available ||
                              item.quantity >= MAX_CART_QUANTITY
                            }
                            className="grid size-11 place-items-center text-xl font-bold text-primary transition-colors hover:bg-primary-soft disabled:cursor-not-allowed disabled:text-muted-foreground disabled:opacity-45"
                            aria-label={`افزایش تعداد ${item.product.name}`}
                          >
                            +
                          </button>
                          <output
                            className="grid min-w-11 place-items-center border-x border-border px-2 text-sm font-black tabular-nums"
                            aria-label={`تعداد ${item.product.name}`}
                          >
                            {item.quantity.toLocaleString("fa-IR")}
                          </output>
                          <button
                            type="button"
                            onClick={() =>
                              updateQuantity(item, item.quantity - 1)
                            }
                            disabled={
                              mutationPending ||
                              !item.is_available ||
                              item.quantity <= 1
                            }
                            className="grid size-11 place-items-center text-xl font-bold text-primary transition-colors hover:bg-primary-soft disabled:cursor-not-allowed disabled:text-muted-foreground disabled:opacity-45"
                            aria-label={`کاهش تعداد ${item.product.name}`}
                          >
                            −
                          </button>
                        </div>
                      </div>

                      <div className="min-w-0 text-end">
                        <p className="text-xs text-muted-foreground">جمع کالا</p>
                        <p className="mt-1 break-words font-black tabular-nums text-primary">
                          <bdi>{formatToman(item.line_total)}</bdi>
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => removeItem(item)}
                      disabled={mutationPending}
                      className="mt-4 inline-flex min-h-11 w-fit items-center gap-2 rounded-full px-3 text-sm font-bold text-destructive transition-colors hover:bg-destructive-soft disabled:cursor-wait disabled:opacity-50"
                    >
                      <span aria-hidden="true">×</span>
                      {pending ? "در حال به‌روزرسانی…" : "حذف از سبد"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <aside
          aria-labelledby="cart-summary-title"
          className="overflow-hidden rounded-[1.5rem] border border-gold/45 bg-surface p-5 shadow-card lg:sticky lg:top-28 xl:p-6"
        >
          <h2
            id="cart-summary-title"
            className="text-lg font-black text-foreground"
          >
            خلاصهٔ سفارش
          </h2>
          <dl className="mt-5 rounded-[1.1rem] bg-background px-4 py-5">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-sm text-muted-foreground">
                جمع {itemCount.toLocaleString("fa-IR")} کالا
              </dt>
              <dd className="break-words text-end text-lg font-black tabular-nums text-lapis">
                <bdi>{formatToman(cart.subtotal)}</bdi>
              </dd>
            </div>
          </dl>

          {hasUnavailableItems ? (
            <p className="mt-4 rounded-lg bg-destructive-soft/65 px-3 py-3 text-xs font-semibold leading-6 text-destructive">
              برای ادامه، کالاهای ناموجود یا دارای کسری موجودی را از سبد حذف
              کنید.
            </p>
          ) : (
            <p className="mt-4 text-xs leading-6 text-muted-foreground">
              قیمت‌ها و موجودی مستقیماً از فروشگاه دریافت شده‌اند.
            </p>
          )}

          {!hasUnavailableItems && checkoutState !== "blocked" ? (
            <Link
              href={checkoutState === "customer" ? "/checkout" : "/login"}
              className="mt-6 inline-flex min-h-13 w-full items-center justify-center rounded-full bg-primary px-5 text-sm font-extrabold text-primary-foreground shadow-[0_14px_30px_-18px_rgb(8_108_104/0.85)] transition hover:bg-primary-hover"
            >
              {checkoutState === "customer"
                ? "ادامه و ثبت سفارش"
                : "ورود برای ثبت سفارش"}
            </Link>
          ) : null}
          {checkoutState === "blocked" ? (
            <p className="mt-4 rounded-lg bg-destructive-soft/60 px-3 py-3 text-xs font-semibold leading-6 text-destructive">
              وضعیت حساب برای ثبت سفارش قابل تأیید نیست. کمی بعد دوباره تلاش
              کنید.
            </p>
          ) : null}
          <Link
            href="/products"
            className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-full px-4 text-sm font-bold text-muted-foreground transition-colors hover:bg-background hover:text-primary"
          >
            ادامهٔ خرید
          </Link>
        </aside>
      </div>
    </>
  );
}
