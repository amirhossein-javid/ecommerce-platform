"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import {
  isOwnProductReview,
  MAX_REVIEW_COMMENT_LENGTH,
  type OwnProductReview,
  type ProductReviewAggregate,
  type PublicProductReview,
} from "@/lib/review-contract";
import {
  aggregateAfterApprovedDeletion,
  REVIEW_STATUS_COPY,
} from "@/lib/review-presentation";

type ProductReviewsProps = {
  productSlug: string;
  reviews: PublicProductReview[];
  aggregate: ProductReviewAggregate;
  publicError: boolean;
  accountState: "guest" | "customer" | "blocked";
};

function Stars({ rating }: { rating: number }) {
  return (
    <span
      role="img"
      aria-label={`${rating.toLocaleString("fa-IR")} از ۵ ستاره`}
      className="inline-flex gap-0.5 text-lg leading-none"
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <span
          key={star}
          aria-hidden="true"
          className={star <= Math.round(rating) ? "text-gold" : "text-border"}
        >
          ★
        </span>
      ))}
    </span>
  );
}

function formatReviewDate(value: string) {
  return new Intl.DateTimeFormat("fa-IR", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

function responseMessage(payload: unknown, fallback: string) {
  if (
    payload &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    "error" in payload &&
    typeof payload.error === "string"
  ) {
    return payload.error;
  }
  return fallback;
}

function OwnReviewCard({
  review,
  onDelete,
  deleting,
}: {
  review: OwnProductReview;
  onDelete: () => void;
  deleting: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const statusDetails = REVIEW_STATUS_COPY[review.status];
  const statusClassName = {
    pending: "border-gold/35 bg-background text-foreground",
    approved: "border-success/20 bg-success-soft text-success",
    rejected: "border-destructive/20 bg-destructive-soft text-destructive",
  }[statusDetails.tone];

  return (
    <article className="rounded-[1.25rem] border border-gold/35 bg-surface p-5 shadow-card sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-black text-foreground">نظر شما</p>
          <p className="mt-1 text-xs text-muted-foreground">
            ثبت‌شده در {formatReviewDate(review.created_at)}
          </p>
        </div>
        <Stars rating={review.rating} />
      </div>
      <p className="mt-4 whitespace-pre-line text-sm leading-8 text-foreground">
        {review.comment}
      </p>
      <div className={`mt-5 rounded-xl border px-4 py-3 text-sm ${statusClassName}`}>
        <p className="font-black">{statusDetails.label}</p>
        <p className="mt-1 leading-7">{statusDetails.message}</p>
      </div>
      {!confirming ? (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="mt-5 inline-flex min-h-11 items-center rounded-full px-4 text-sm font-bold text-destructive transition-colors hover:bg-destructive-soft"
        >
          حذف نظر
        </button>
      ) : (
        <div className="mt-5 rounded-xl border border-destructive/20 bg-destructive-soft/45 p-4">
          <p className="text-sm font-bold leading-7 text-foreground">
            این نظر حذف شود؟ پس از حذف می‌توانید نظر تازه‌ای ثبت کنید.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onDelete}
              disabled={deleting}
              className="inline-flex min-h-11 items-center rounded-full bg-destructive px-4 text-sm font-bold text-white disabled:opacity-60"
            >
              {deleting ? "در حال حذف…" : "بله، حذف شود"}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              disabled={deleting}
              className="inline-flex min-h-11 items-center rounded-full border border-gold/40 bg-surface px-4 text-sm font-bold"
            >
              انصراف
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

export function ProductReviews({
  productSlug,
  reviews,
  aggregate,
  publicError,
  accountState,
}: ProductReviewsProps) {
  const router = useRouter();
  const [ownReview, setOwnReview] = useState<OwnProductReview | null>();
  const [visibleReviews, setVisibleReviews] = useState(reviews);
  const [visibleAggregate, setVisibleAggregate] = useState(aggregate);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (accountState !== "customer") return;
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(
          `/api/products/${encodeURIComponent(productSlug)}/reviews/mine`,
          { cache: "no-store", signal: controller.signal },
        );
        const payload: unknown = await response.json();
        if (!response.ok) {
          setError(responseMessage(payload, "دریافت نظر شما ممکن نشد."));
          setOwnReview(null);
          return;
        }
        if (
          payload &&
          typeof payload === "object" &&
          !Array.isArray(payload) &&
          "review" in payload &&
          (payload.review === null || isOwnProductReview(payload.review))
        ) {
          setOwnReview(payload.review);
        } else {
          setError("پاسخ سرویس نظرها معتبر نبود.");
          setOwnReview(null);
        }
      } catch (caught) {
        if (!(caught instanceof DOMException && caught.name === "AbortError")) {
          setError("ارتباط با سرویس نظرها برقرار نشد.");
          setOwnReview(null);
        }
      }
    })();
    return () => controller.abort();
  }, [accountState, productSlug]);

  const submitReview = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    const normalizedComment = comment.trim();
    if (rating < 1 || rating > 5) {
      setError("یک امتیاز از ۱ تا ۵ انتخاب کنید.");
      return;
    }
    if (!normalizedComment) {
      setError("متن نظر را وارد کنید.");
      return;
    }
    setPending(true);
    try {
      const response = await fetch(
        `/api/products/${encodeURIComponent(productSlug)}/reviews/mine`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rating, comment: normalizedComment }),
        },
      );
      const payload: unknown = await response.json();
      if (!response.ok) {
        setError(responseMessage(payload, "ثبت نظر ممکن نشد."));
        return;
      }
      if (
        payload &&
        typeof payload === "object" &&
        !Array.isArray(payload) &&
        "review" in payload &&
        isOwnProductReview(payload.review)
      ) {
        setOwnReview(payload.review);
        setRating(0);
        setComment("");
        setSuccess("نظر شما ثبت شد و در انتظار بررسی مدیر است.");
      } else {
        setError("پاسخ ثبت نظر معتبر نبود.");
      }
    } catch {
      setError("ارتباط با سرویس نظرها برقرار نشد.");
    } finally {
      setPending(false);
    }
  };

  const deleteReview = async () => {
    setPending(true);
    setError("");
    setSuccess("");
    try {
      const response = await fetch(
        `/api/products/${encodeURIComponent(productSlug)}/reviews/mine`,
        { method: "DELETE" },
      );
      const payload: unknown = await response.json();
      if (!response.ok) {
        setError(responseMessage(payload, "حذف نظر ممکن نشد."));
        return;
      }
      if (ownReview?.status === "APPROVED") {
        const deletedReview = ownReview;
        setVisibleReviews((current) =>
          current.filter((review) => review.id !== deletedReview.id),
        );
        setVisibleAggregate((current) =>
          aggregateAfterApprovedDeletion(current, deletedReview.rating),
        );
      }
      setOwnReview(null);
      setSuccess("نظر حذف شد. اکنون می‌توانید نظر تازه‌ای ثبت کنید.");
      router.refresh();
    } catch {
      setError("ارتباط با سرویس نظرها برقرار نشد.");
    } finally {
      setPending(false);
    }
  };

  return (
    <section aria-labelledby="product-reviews-title" className="mt-10 border-t border-gold/35 pt-8 sm:mt-14 sm:pt-10">
      <div className="grid gap-7 lg:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)] lg:items-start">
        <div>
          <p className="text-xs font-black text-primary">تجربهٔ مشتریان</p>
          <h2 id="product-reviews-title" className="mt-2 text-2xl font-black text-foreground">
            نظرها و امتیازها
          </h2>
          {publicError ? (
            <p role="alert" className="mt-5 rounded-xl border border-destructive/20 bg-destructive-soft px-4 py-3 text-sm font-semibold text-destructive">
              دریافت نظرهای عمومی ممکن نشد. کمی بعد دوباره تلاش کنید.
            </p>
          ) : visibleAggregate.review_count > 0 && visibleAggregate.average_rating ? (
            <div className="mt-5 rounded-[1.25rem] border border-gold/35 bg-surface p-5 shadow-card">
              <div className="flex items-end gap-3">
                <strong className="text-4xl font-black tabular-nums text-lapis">
                  {Number(visibleAggregate.average_rating).toLocaleString("fa-IR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                </strong>
                <span className="pb-1 text-sm text-muted-foreground">از ۵</span>
              </div>
              <div className="mt-3"><Stars rating={Number(visibleAggregate.average_rating)} /></div>
              <p className="mt-3 text-sm text-muted-foreground">
                بر پایهٔ {visibleAggregate.review_count.toLocaleString("fa-IR")} نظر تأییدشده
              </p>
            </div>
          ) : (
            <p className="mt-5 rounded-[1.25rem] border border-gold/35 bg-surface px-5 py-7 text-sm leading-8 text-muted-foreground shadow-card">
              هنوز نظر تأییدشده‌ای برای این محصول ثبت نشده است.
            </p>
          )}

          <div className="mt-6">
            {accountState === "guest" ? (
              <div className="rounded-[1.25rem] border border-primary/15 bg-primary-soft/65 p-5 text-sm leading-8">
                برای ثبت نظر باید وارد حساب مشتری شوید.
                <Link href={`/login?next=${encodeURIComponent(`/products/${productSlug}`)}`} className="mr-2 font-black text-primary underline decoration-gold underline-offset-4">
                  ورود به حساب
                </Link>
              </div>
            ) : accountState === "blocked" ? (
              <p className="rounded-[1.25rem] border border-destructive/20 bg-destructive-soft p-5 text-sm leading-8 text-destructive">
                وضعیت حساب برای ثبت نظر قابل تأیید نیست. کمی بعد دوباره تلاش کنید.
              </p>
            ) : ownReview === undefined ? (
              <p role="status" className="rounded-[1.25rem] border border-gold/35 bg-surface p-5 text-sm text-muted-foreground">
                در حال دریافت وضعیت نظر شما…
              </p>
            ) : ownReview ? (
              <OwnReviewCard review={ownReview} onDelete={deleteReview} deleting={pending} />
            ) : (
              <form onSubmit={submitReview} className="rounded-[1.25rem] border border-gold/35 bg-surface p-5 shadow-card sm:p-6">
                <h3 className="text-lg font-black text-foreground">نظر شما دربارهٔ این محصول</h3>
                <fieldset className="mt-5">
                  <legend className="text-sm font-bold text-foreground">امتیاز</legend>
                  <div className="mt-2 flex w-fit flex-row-reverse gap-1" dir="ltr">
                    {[5, 4, 3, 2, 1].map((value) => (
                      <label key={value} className="cursor-pointer">
                        <input
                          type="radio"
                          name="rating"
                          value={value}
                          checked={rating === value}
                          onChange={() => setRating(value)}
                          className="sr-only"
                          disabled={pending}
                        />
                        <span
                          aria-hidden="true"
                          className={`grid size-11 place-items-center rounded-full text-2xl transition-colors ${value <= rating ? "bg-primary-soft text-gold" : "text-border hover:bg-background hover:text-gold"}`}
                        >
                          ★
                        </span>
                        <span className="sr-only">{value} از ۵</span>
                      </label>
                    ))}
                  </div>
                </fieldset>
                <label htmlFor="review-comment" className="mt-5 block text-sm font-bold text-foreground">
                  متن نظر
                </label>
                <textarea
                  id="review-comment"
                  required
                  rows={5}
                  maxLength={MAX_REVIEW_COMMENT_LENGTH}
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  disabled={pending}
                  className="mt-2 w-full resize-y rounded-[1rem] border border-border bg-background px-4 py-3 text-sm leading-8 text-foreground placeholder:text-muted-foreground focus:border-primary disabled:opacity-60"
                  placeholder="تجربهٔ خود از کیفیت و ویژگی‌های محصول را بنویسید."
                />
                <p className="mt-2 text-xs leading-6 text-muted-foreground">
                  نظر پس از بررسی مدیر به‌صورت عمومی نمایش داده می‌شود و قابل ویرایش نیست.
                </p>
                <button type="submit" disabled={pending} className="mt-5 inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 text-sm font-black text-primary-foreground transition-colors hover:bg-primary-hover disabled:cursor-wait disabled:opacity-60">
                  {pending ? "در حال ثبت…" : "ثبت نظر"}
                </button>
              </form>
            )}
          </div>

          <div className="mt-4 min-h-7" aria-live="polite">
            {error ? <p role="alert" className="rounded-xl border border-destructive/20 bg-destructive-soft px-4 py-3 text-sm font-semibold text-destructive">{error}</p> : null}
            {success ? <p role="status" className="rounded-xl border border-success/20 bg-success-soft px-4 py-3 text-sm font-semibold text-success">{success}</p> : null}
          </div>
        </div>

        <div aria-label="نظرهای تأییدشده" className="space-y-4">
          {!publicError && visibleReviews.length === 0 ? (
            <div className="rounded-[1.5rem] border border-gold/35 bg-surface px-5 py-12 text-center shadow-card">
              <p className="font-black text-foreground">هنوز نظری برای نمایش نیست</p>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">پس از تأیید نظرها، تجربهٔ مشتریان در این بخش نمایش داده می‌شود.</p>
            </div>
          ) : null}
          {visibleReviews.map((review) => (
            <article key={review.id} className="rounded-[1.5rem] border border-gold/35 bg-surface p-5 shadow-card sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-black text-foreground">{review.author_name}</h3>
                  <time dateTime={review.created_at} className="mt-1 block text-xs text-muted-foreground">
                    {formatReviewDate(review.created_at)}
                  </time>
                </div>
                <Stars rating={review.rating} />
              </div>
              <p className="mt-4 whitespace-pre-line text-sm leading-8 text-foreground sm:text-base sm:leading-9">{review.comment}</p>
            </article>
          ))}
          {!publicError && visibleAggregate.review_count > visibleReviews.length ? (
            <p className="px-2 text-xs leading-6 text-muted-foreground">
              تازه‌ترین {visibleReviews.length.toLocaleString("fa-IR")} نظر از {visibleAggregate.review_count.toLocaleString("fa-IR")} نظر تأییدشده نمایش داده شده است.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
