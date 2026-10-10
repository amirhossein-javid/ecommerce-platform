"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import type { CustomerAddress } from "@/lib/address-contract";
import type { Cart } from "@/lib/cart-contract";
import { isCheckoutOrder } from "@/lib/checkout-contract";
import { formatToman } from "@/lib/format-price";

type CheckoutViewProps = {
  addresses: CustomerAddress[];
  cart: Cart;
};

type CheckoutErrorPayload = {
  error?: unknown;
  code?: unknown;
};

function ProductPlaceholder() {
  return (
    <div className="grid size-full place-items-center bg-surface-muted/60 text-muted-foreground">
      <svg aria-hidden="true" viewBox="0 0 48 48" fill="none" className="size-8">
        <path d="M8 15.5 24 7l16 8.5v17L24 41 8 32.5v-17Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
        <path d="m8.5 15.5 15.5 9 15.5-9M24 24.5V41" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

async function readError(response: Response) {
  try {
    return (await response.json()) as CheckoutErrorPayload;
  } catch {
    return {};
  }
}

export function CheckoutView({ addresses, cart }: CheckoutViewProps) {
  const router = useRouter();
  const submitLock = useRef(false);
  const initialAddress =
    addresses.find((address) => address.is_default)?.id ?? addresses[0]?.id;
  const [addressId, setAddressId] = useState<number | undefined>(initialAddress);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [outcomeUnknown, setOutcomeUnknown] = useState(false);

  const hasUnavailableItems = cart.items.some((item) => !item.is_available);
  const canSubmit =
    cart.items.length > 0 &&
    addresses.length > 0 &&
    addressId !== undefined &&
    !hasUnavailableItems &&
    !pending &&
    !outcomeUnknown;

  const submitOrder = async () => {
    if (!canSubmit || submitLock.current || addressId === undefined) return;
    submitLock.current = true;
    setPending(true);
    setError("");

    try {
      const response = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ addressId }),
      });

      if (response.status === 401) {
        router.push("/login");
        router.refresh();
        return;
      }

      if (!response.ok) {
        const payload = await readError(response);
        const message =
          typeof payload.error === "string"
            ? payload.error
            : "ثبت سفارش ممکن نشد. دوباره تلاش کنید.";
        setError(message);
        if (payload.code === "outcome-unknown") {
          setOutcomeUnknown(true);
          return;
        }
        submitLock.current = false;
        return;
      }

      const payload: unknown = await response.json();
      if (!isCheckoutOrder(payload)) {
        setError("پاسخ ثبت سفارش معتبر نبود. برای جلوگیری از سفارش تکراری، وضعیت سبد را بررسی کنید.");
        setOutcomeUnknown(true);
        return;
      }

      router.push(`/checkout/orders/${payload.id}`);
      router.refresh();
    } catch {
      setError("پاسخ ثبت سفارش دریافت نشد و نتیجه مشخص نیست. برای جلوگیری از سفارش تکراری، دوباره ارسال نکنید و وضعیت سبد را بررسی کنید.");
      setOutcomeUnknown(true);
    } finally {
      setPending(false);
    }
  };

  if (cart.items.length === 0) {
    return (
      <section className="rounded-[1.5rem] border border-gold/40 bg-surface px-5 py-14 text-center shadow-card sm:px-8 sm:py-20">
        <h2 className="text-xl font-black text-foreground sm:text-2xl">سبد خرید برای ثبت سفارش خالی است</h2>
        <p className="mx-auto mt-3 max-w-lg leading-8 text-muted-foreground">ابتدا محصولی به سبد خرید اضافه کنید و سپس به این مرحله برگردید.</p>
        <Link href="/products" className="mt-7 inline-flex min-h-11 items-center justify-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">مشاهدهٔ محصولات</Link>
      </section>
    );
  }

  return (
    <div className="grid min-w-0 gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start xl:gap-10">
      <div className="min-w-0 space-y-9">
        <section aria-labelledby="checkout-address-title" className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gold/30 pb-4">
            <div>
              <p className="text-xs font-bold text-primary">مرحلهٔ ۱</p>
              <h2 id="checkout-address-title" className="mt-1 text-xl font-black text-foreground">آدرس دریافت سفارش</h2>
            </div>
            <Link href="/account/addresses" className="inline-flex min-h-11 items-center rounded-full border border-primary/30 bg-surface px-4 text-sm font-bold text-primary hover:border-primary/55 hover:bg-primary-soft/50">مدیریت آدرس‌ها</Link>
          </div>

          {addresses.length === 0 ? (
            <div className="mt-5 rounded-[1.25rem] border border-primary/15 bg-primary-soft/45 px-5 py-6">
              <h3 className="font-black text-foreground">هنوز آدرسی ثبت نشده است</h3>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">برای ثبت سفارش، ابتدا یک آدرس دریافت معتبر اضافه کنید.</p>
              <Link href="/account/addresses" className="mt-5 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">افزودن آدرس</Link>
            </div>
          ) : (
            <fieldset className="mt-5 grid gap-3">
              <legend className="sr-only">انتخاب آدرس دریافت سفارش</legend>
              {addresses.map((address) => {
                const selected = address.id === addressId;
                return (
                  <label key={address.id} className={`relative flex cursor-pointer gap-3 rounded-[1.25rem] border p-4 transition-colors sm:p-5 ${selected ? "border-primary bg-primary-soft/35 shadow-[0_10px_24px_-22px_rgb(8_108_104/0.7)]" : "border-gold/35 bg-background hover:border-primary/35"}`}>
                    <input type="radio" name="address" value={address.id} checked={selected} onChange={() => setAddressId(address.id)} disabled={pending || outcomeUnknown} className="mt-1 size-5 shrink-0 accent-primary disabled:cursor-not-allowed" />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <strong className="text-sm text-foreground">{address.title || "آدرس دریافت"}</strong>
                        {address.is_default ? <span className="rounded-md bg-surface px-2 py-1 text-[0.7rem] font-bold text-primary">پیش‌فرض</span> : null}
                      </span>
                      <span className="mt-2 block text-sm font-semibold text-foreground">{address.recipient_first_name} {address.recipient_last_name}</span>
                      <span className="mt-1 block break-words text-sm leading-7 text-muted-foreground">{address.province}، {address.city}، {address.address}</span>
                      <span className="mt-2 block text-xs text-muted-foreground"><bdi dir="ltr">{address.recipient_phone_number}</bdi> · کد پستی <bdi>{address.postal_code}</bdi></span>
                    </span>
                  </label>
                );
              })}
            </fieldset>
          )}
        </section>

        <section aria-labelledby="checkout-items-title" className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-6">
          <div className="flex items-end justify-between gap-4 border-b border-gold/30 pb-4">
            <div>
              <p className="text-xs font-bold text-primary">مرحلهٔ ۲</p>
              <h2 id="checkout-items-title" className="mt-1 text-xl font-black text-foreground">مرور کالاها</h2>
            </div>
            <Link href="/cart" className="inline-flex min-h-11 items-center px-2 text-sm font-bold text-primary hover:underline">ویرایش سبد</Link>
          </div>
          <div className="divide-y divide-gold/30">
            {cart.items.map((item) => {
              const image = item.product.primary_image;
              return (
                <article key={item.id} className="grid grid-cols-[5rem_minmax(0,1fr)] gap-4 py-5 sm:grid-cols-[6rem_minmax(0,1fr)]">
                  <Link href={`/products/${item.product.slug}`} className="aspect-square overflow-hidden rounded-xl border border-gold/35 bg-background" aria-label={`مشاهدهٔ ${item.product.name}`}>
                    {image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={image.image} alt={image.alt_text || item.product.name} className="size-full object-contain p-2" />
                    ) : <ProductPlaceholder />}
                  </Link>
                  <div className="min-w-0">
                    <Link href={`/products/${item.product.slug}`} className="line-clamp-2 text-sm font-extrabold leading-7 text-foreground hover:text-primary sm:text-base">{item.product.name}</Link>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
                      <span className="text-muted-foreground">تعداد: <bdi className="font-bold text-foreground">{item.quantity.toLocaleString("fa-IR")}</bdi></span>
                      <strong className="tabular-nums text-primary"><bdi>{formatToman(item.line_total)}</bdi></strong>
                    </div>
                    {!item.is_available ? <p className="mt-3 rounded-lg bg-destructive-soft/65 px-3 py-2 text-xs font-semibold leading-6 text-destructive">این کالا با تعداد فعلی قابل سفارش نیست؛ سبد خرید را اصلاح کنید.</p> : null}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>

      <aside aria-labelledby="checkout-summary-title" className="rounded-[1.5rem] border border-gold/45 bg-surface p-5 shadow-card lg:sticky lg:top-28 xl:p-6">
        <h2 id="checkout-summary-title" className="text-lg font-black text-foreground">خلاصهٔ ثبت سفارش</h2>
        <dl className="mt-5 rounded-[1.1rem] bg-background px-4 py-5">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-sm text-muted-foreground">جمع فعلی کالاها</dt>
            <dd className="break-words text-end text-lg font-black tabular-nums text-lapis"><bdi>{formatToman(cart.subtotal)}</bdi></dd>
          </div>
        </dl>
        <p className="mt-4 text-xs leading-6 text-muted-foreground">قیمت و موجودی هنگام ثبت، دوباره توسط فروشگاه بررسی می‌شود. این مرحله پرداخت نیست.</p>

        {hasUnavailableItems ? <p className="mt-4 rounded-lg bg-destructive-soft/65 px-3 py-3 text-xs font-semibold leading-6 text-destructive">برای ادامه، کالاهای ناموجود یا دارای کسری موجودی را در سبد اصلاح کنید.</p> : null}
        {error ? <p role="alert" className="mt-4 rounded-lg bg-destructive-soft px-3 py-3 text-xs font-semibold leading-6 text-destructive">{error}</p> : null}
        {outcomeUnknown ? <Link href="/cart" className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-primary/35 px-4 text-sm font-bold text-primary hover:bg-primary-soft/55">بررسی وضعیت سبد</Link> : null}

        <button type="button" onClick={submitOrder} disabled={!canSubmit} className="mt-6 inline-flex min-h-13 w-full items-center justify-center rounded-full bg-primary px-5 text-sm font-extrabold text-primary-foreground transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:bg-muted-foreground/45">
          {pending ? "در حال ثبت سفارش…" : "ثبت سفارش"}
        </button>
        <Link href="/cart" className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-full px-4 text-sm font-bold text-muted-foreground hover:bg-background hover:text-primary">بازگشت به سبد خرید</Link>
      </aside>
    </div>
  );
}
