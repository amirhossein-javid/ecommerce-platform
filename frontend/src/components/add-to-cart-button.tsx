"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { isCart, MAX_CART_QUANTITY } from "@/lib/cart-contract";
import { formatToman, multiplyWholeRialPrice } from "@/lib/format-price";

type AddToCartButtonProps = {
  productPrice: string;
  productSlug: string;
};

async function getResponseError(response: Response) {
  try {
    const payload = (await response.json()) as { error?: unknown };
    return typeof payload.error === "string"
      ? payload.error
      : "افزودن محصول به سبد خرید ممکن نشد.";
  } catch {
    return "افزودن محصول به سبد خرید ممکن نشد.";
  }
}

export function AddToCartButton({
  productPrice,
  productSlug,
}: AddToCartButtonProps) {
  const router = useRouter();
  const submissionLock = useRef(false);
  const [quantity, setQuantity] = useState(1);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [added, setAdded] = useState(false);
  const selectedTotal = multiplyWholeRialPrice(productPrice, quantity);

  const changeQuantity = (nextQuantity: number) => {
    if (
      pending ||
      !Number.isSafeInteger(nextQuantity) ||
      nextQuantity < 1 ||
      nextQuantity > MAX_CART_QUANTITY
    ) {
      return;
    }

    setQuantity(nextQuantity);
    setError("");
    setAdded(false);
  };

  const addToCart = async () => {
    if (submissionLock.current) {
      return;
    }

    submissionLock.current = true;
    setPending(true);
    setError("");
    setAdded(false);

    try {
      const response = await fetch("/api/cart/items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ productSlug, quantity }),
      });

      if (!response.ok) {
        setError(await getResponseError(response));
        return;
      }

      const payload: unknown = await response.json();

      if (!isCart(payload)) {
        setError("پاسخ سبد خرید معتبر نبود. دوباره تلاش کنید.");
        return;
      }

      setAdded(true);
      router.refresh();
    } catch {
      setError("ارتباط با سبد خرید برقرار نشد. دوباره تلاش کنید.");
    } finally {
      submissionLock.current = false;
      setPending(false);
    }
  };

  return (
    <div>
      <div className="mb-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p
              id="product-quantity-label"
              className="text-sm font-bold text-foreground"
            >
              تعداد
            </p>
            <div
              role="group"
              aria-labelledby="product-quantity-label"
              className="mt-2 inline-flex min-h-11 items-center overflow-hidden rounded-full border border-gold/45 bg-background"
            >
              <button
                type="button"
                onClick={() => changeQuantity(quantity + 1)}
                disabled={pending || quantity >= MAX_CART_QUANTITY}
                className="grid size-11 place-items-center text-xl font-bold text-primary transition-colors hover:bg-primary-soft disabled:cursor-not-allowed disabled:text-muted-foreground disabled:opacity-45"
                aria-label="افزایش تعداد"
              >
                +
              </button>
              <output
                className="grid min-w-11 place-items-center border-x border-border px-2 text-sm font-black tabular-nums"
                aria-label="تعداد انتخاب‌شده"
                aria-live="polite"
              >
                {quantity.toLocaleString("fa-IR")}
              </output>
              <button
                type="button"
                onClick={() => changeQuantity(quantity - 1)}
                disabled={pending || quantity <= 1}
                className="grid size-11 place-items-center text-xl font-bold text-primary transition-colors hover:bg-primary-soft disabled:cursor-not-allowed disabled:text-muted-foreground disabled:opacity-45"
                aria-label="کاهش تعداد"
              >
                −
              </button>
            </div>
          </div>

          <div className="min-w-0 text-end">
            <p className="text-xs font-semibold text-muted-foreground">
              جمع انتخاب‌شده
            </p>
            <p className="mt-1 break-words text-sm font-black leading-7 tabular-nums text-primary">
              <bdi>
                {selectedTotal ? formatToman(selectedTotal) : "قیمت نامعتبر"}
              </bdi>
            </p>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={addToCart}
        disabled={pending}
        className="inline-flex min-h-13 w-full items-center justify-center gap-2 rounded-full bg-primary px-5 text-sm font-extrabold text-primary-foreground shadow-[0_14px_30px_-18px_rgb(8_108_104/0.85)] transition hover:bg-primary-hover hover:shadow-card disabled:cursor-wait disabled:opacity-65"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          className="size-5"
        >
          <path
            d="M4 5h2l1.5 9h9.75l1.5-6H7M10 18.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm8 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {pending ? "در حال افزودن…" : "افزودن به سبد خرید"}
      </button>

      <div className="mt-3 min-h-7 text-sm" aria-live="polite">
        {added ? (
          <p className="font-bold text-success">
            {quantity.toLocaleString("fa-IR")} عدد به سبد اضافه شد.{" "}
            <Link href="/cart" className="underline underline-offset-4">
              مشاهدهٔ سبد
            </Link>
          </p>
        ) : null}
        {error ? <p className="font-semibold text-destructive">{error}</p> : null}
      </div>
    </div>
  );
}
