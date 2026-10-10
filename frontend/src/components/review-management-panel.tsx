"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  isManagedReview,
  isManagedReviewPage,
  isStoreReply,
  MAX_STORE_REPLY_LENGTH,
  type ManagedReview,
  type ManagedReviewPage,
  type ManagedReviewStatus,
} from "@/lib/management-review-contract";

const STATUS_COPY: Record<ManagedReviewStatus, string> = {
  PENDING: "در انتظار بررسی",
  APPROVED: "تأییدشده",
  REJECTED: "ردشده",
};

const EMPTY_FILTERS = { status: "", hasReply: "", search: "" };

function responseError(payload: unknown, fallback: string) {
  return payload &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    "error" in payload &&
    typeof payload.error === "string"
    ? payload.error
    : fallback;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ReviewManagementPanel() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [page, setPage] = useState<ManagedReviewPage | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [replyFilter, setReplyFilter] = useState("");
  const [search, setSearch] = useState("");
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [currentPage, setCurrentPage] = useState(1);
  const [replyText, setReplyText] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selected = useMemo(
    () => page?.results.find((review) => review.id === selectedId) ?? null,
    [page, selectedId],
  );

  const loadReviews = useCallback(
    async (requestedPage = 1, filters = EMPTY_FILTERS) => {
      setLoading(true);
      setError("");
      const query = new URLSearchParams();
      if (filters.status) query.set("status", filters.status);
      if (filters.hasReply) query.set("has_reply", filters.hasReply);
      if (filters.search) query.set("search", filters.search);
      if (requestedPage > 1) query.set("page", String(requestedPage));
      try {
        const response = await fetch(`/api/management/reviews?${query}`, {
          cache: "no-store",
        });
        const payload: unknown = await response.json();
        if (response.status === 401) {
          setAuthenticated(false);
          setPage(null);
          setSelectedId(null);
          return;
        }
        if (!response.ok || !isManagedReviewPage(payload)) {
          setAuthenticated(true);
          setError(responseError(payload, "دریافت فهرست نظرها ممکن نشد."));
          return;
        }
        setAuthenticated(true);
        setPage(payload);
        setCurrentPage(requestedPage);
        const next = payload.results[0] ?? null;
        setSelectedId(next?.id ?? null);
        setReplyText(next?.store_reply?.comment ?? "");
      } catch {
        setError("ارتباط با پنل مدیریت برقرار نشد.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => void loadReviews(), 0);
    return () => window.clearTimeout(timer);
  }, [loadReviews]);

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/management/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: String(form.get("email") ?? ""),
          password: String(form.get("password") ?? ""),
        }),
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        setError(responseError(payload, "ورود به پنل ممکن نشد."));
        return;
      }
      setAuthenticated(true);
      await loadReviews(1);
    } catch {
      setError("ارتباط با سرویس ورود برقرار نشد.");
    } finally {
      setPending(false);
    }
  };

  const logout = async () => {
    setPending(true);
    try {
      await fetch("/api/management/auth/logout", { method: "POST" });
    } finally {
      setAuthenticated(false);
      setPage(null);
      setPending(false);
    }
  };

  const applyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const filters = {
      status: statusFilter,
      hasReply: replyFilter,
      search: search.trim(),
    };
    setAppliedFilters(filters);
    void loadReviews(1, filters);
  };

  const replaceReview = (review: ManagedReview) => {
    setPage((current) =>
      current
        ? {
            ...current,
            results: current.results.map((item) =>
              item.id === review.id ? review : item,
            ),
          }
        : current,
    );
  };

  const moderate = async (status: "APPROVED" | "REJECTED") => {
    if (!selected) return;
    setPending(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(
        `/api/management/reviews/${selected.id}/moderate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        },
      );
      const payload: unknown = await response.json();
      if (!response.ok || !isManagedReview(payload)) {
        setError(responseError(payload, "تغییر وضعیت نظر ممکن نشد."));
        return;
      }
      replaceReview(payload);
      setNotice(status === "APPROVED" ? "نظر تأیید شد." : "نظر رد شد.");
    } catch {
      setError("ارتباط با سرویس مدیریت برقرار نشد.");
    } finally {
      setPending(false);
    }
  };

  const saveReply = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    const comment = replyText.trim();
    if (!comment || comment.length > MAX_STORE_REPLY_LENGTH) {
      setError("متن پاسخ باید بین ۱ تا ۵۰۰۰ نویسه باشد.");
      return;
    }
    setPending(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(
        `/api/management/reviews/${selected.id}/reply`,
        {
          method: selected.store_reply ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ comment }),
        },
      );
      const payload: unknown = await response.json();
      if (!response.ok || !isStoreReply(payload)) {
        setError(responseError(payload, "ذخیرهٔ پاسخ ممکن نشد."));
        return;
      }
      replaceReview({ ...selected, store_reply: payload });
      setReplyText(payload.comment);
      setNotice(selected.store_reply ? "پاسخ ویرایش شد." : "پاسخ ثبت شد.");
    } catch {
      setError("ارتباط با سرویس مدیریت برقرار نشد.");
    } finally {
      setPending(false);
    }
  };

  const deleteReply = async () => {
    if (!selected?.store_reply || !window.confirm("پاسخ رسمی حذف شود؟")) return;
    setPending(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(
        `/api/management/reviews/${selected.id}/reply`,
        { method: "DELETE" },
      );
      const payload: unknown = await response.json();
      if (!response.ok) {
        setError(responseError(payload, "حذف پاسخ ممکن نشد."));
        return;
      }
      replaceReview({ ...selected, store_reply: null });
      setReplyText("");
      setNotice("پاسخ حذف شد.");
    } catch {
      setError("ارتباط با سرویس مدیریت برقرار نشد.");
    } finally {
      setPending(false);
    }
  };

  if (authenticated === null || (loading && !page)) {
    return (
      <div role="status" className="rounded-2xl border border-gold/35 bg-surface p-8 text-center text-sm text-muted-foreground shadow-card">
        در حال بررسی نشست مدیریت…
      </div>
    );
  }

  if (!authenticated) {
    return (
      <form onSubmit={login} className="mx-auto max-w-md rounded-[1.5rem] border border-gold/40 bg-surface p-6 shadow-card sm:p-8">
        <h2 className="text-xl font-black text-foreground">ورود اپراتور</h2>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">فقط حساب کارکنان دارای مجوز صریح مدیریت نظرها پذیرفته می‌شود.</p>
        <label htmlFor="management-email" className="mt-6 block text-sm font-bold">ایمیل</label>
        <input id="management-email" name="email" type="email" autoComplete="username" required className="mt-2 min-h-12 w-full rounded-xl border border-border bg-background px-4 outline-none focus:border-primary" />
        <label htmlFor="management-password" className="mt-4 block text-sm font-bold">رمز عبور</label>
        <input id="management-password" name="password" type="password" autoComplete="current-password" required className="mt-2 min-h-12 w-full rounded-xl border border-border bg-background px-4 outline-none focus:border-primary" />
        {error ? <p role="alert" className="mt-4 rounded-xl bg-destructive-soft px-4 py-3 text-sm font-bold text-destructive">{error}</p> : null}
        <button disabled={pending} className="mt-6 min-h-12 w-full rounded-full bg-primary px-5 font-black text-primary-foreground disabled:opacity-60">{pending ? "در حال ورود…" : "ورود به مدیریت نظرها"}</button>
      </form>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gold/35 bg-surface p-4 shadow-card">
        <div>
          <p className="text-sm font-black text-foreground">نشست اپراتور فعال است</p>
          <p className="text-xs text-muted-foreground">پاسخ‌ها و وضعیت‌ها مستقیماً در Django ذخیره می‌شوند.</p>
        </div>
        <button type="button" onClick={logout} disabled={pending} className="min-h-10 rounded-full border border-border px-4 text-sm font-bold hover:bg-background">خروج</button>
      </div>

      <form onSubmit={applyFilters} className="grid gap-3 rounded-2xl border border-gold/35 bg-surface p-4 shadow-card sm:grid-cols-2 lg:grid-cols-[1fr_13rem_13rem_auto]">
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="جست‌وجوی محصول، مشتری یا متن نظر" maxLength={255} className="min-h-11 rounded-xl border border-border bg-background px-4 text-sm outline-none focus:border-primary" />
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="min-h-11 rounded-xl border border-border bg-background px-3 text-sm">
          <option value="">همهٔ وضعیت‌ها</option>
          <option value="PENDING">در انتظار بررسی</option>
          <option value="APPROVED">تأییدشده</option>
          <option value="REJECTED">ردشده</option>
        </select>
        <select value={replyFilter} onChange={(event) => setReplyFilter(event.target.value)} className="min-h-11 rounded-xl border border-border bg-background px-3 text-sm">
          <option value="">با پاسخ و بی‌پاسخ</option>
          <option value="true">دارای پاسخ رسمی</option>
          <option value="false">بدون پاسخ رسمی</option>
        </select>
        <button disabled={loading} className="min-h-11 rounded-full bg-lapis px-5 text-sm font-black text-white disabled:opacity-60">اعمال فیلتر</button>
      </form>

      {error ? <p role="alert" className="rounded-xl border border-destructive/20 bg-destructive-soft px-4 py-3 text-sm font-bold text-destructive">{error}</p> : null}
      {notice ? <p role="status" className="rounded-xl border border-success/20 bg-success-soft px-4 py-3 text-sm font-bold text-success">{notice}</p> : null}

      <div className="grid gap-5 lg:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)] lg:items-start">
        <section aria-label="فهرست نظرها" className="space-y-3">
          <p className="px-1 text-sm font-bold text-muted-foreground">{page?.count.toLocaleString("fa-IR") ?? "۰"} نظر</p>
          {page?.results.map((review) => (
            <button key={review.id} type="button" onClick={() => { setSelectedId(review.id); setReplyText(review.store_reply?.comment ?? ""); setError(""); setNotice(""); }} className={`w-full rounded-2xl border p-4 text-start shadow-card transition ${selectedId === review.id ? "border-primary bg-primary-soft/45" : "border-gold/35 bg-surface hover:border-primary/45"}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong>{review.product.name}</strong>
                <span className="rounded-full bg-background px-3 py-1 text-xs font-bold">{STATUS_COPY[review.status]}</span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{review.customer_display_name} · امتیاز {review.rating.toLocaleString("fa-IR")} از ۵</p>
              <p className="mt-3 line-clamp-2 text-sm leading-7">{review.comment}</p>
            </button>
          ))}
          {!loading && page?.results.length === 0 ? <p className="rounded-2xl border border-gold/35 bg-surface p-8 text-center text-sm text-muted-foreground">نظری مطابق فیلترها پیدا نشد.</p> : null}
          <div className="flex items-center justify-between gap-3">
            <button type="button" disabled={!page?.previous || loading} onClick={() => void loadReviews(currentPage - 1, appliedFilters)} className="min-h-10 rounded-full border border-border px-4 text-sm font-bold disabled:opacity-40">صفحهٔ قبل</button>
            <span className="text-xs text-muted-foreground">صفحهٔ {currentPage.toLocaleString("fa-IR")}</span>
            <button type="button" disabled={!page?.next || loading} onClick={() => void loadReviews(currentPage + 1, appliedFilters)} className="min-h-10 rounded-full border border-border px-4 text-sm font-bold disabled:opacity-40">صفحهٔ بعد</button>
          </div>
        </section>

        <section aria-label="جزئیات نظر" className="lg:sticky lg:top-24">
          {selected ? (
            <article className="rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-7">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link href={`/products/${encodeURIComponent(selected.product.slug)}`} className="text-lg font-black text-lapis hover:text-primary">{selected.product.name}</Link>
                  <p className="mt-1 text-sm text-muted-foreground">{selected.customer_display_name}</p>
                </div>
                <span className="rounded-full bg-background px-3 py-1 text-xs font-black">{STATUS_COPY[selected.status]}</span>
              </div>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div><dt className="text-muted-foreground">امتیاز</dt><dd className="font-black text-gold">{"★".repeat(selected.rating)}<span className="text-border">{"★".repeat(5 - selected.rating)}</span></dd></div>
                <div><dt className="text-muted-foreground">زمان ثبت</dt><dd className="font-bold">{formatDate(selected.created_at)}</dd></div>
              </dl>
              <div className="mt-5 rounded-xl bg-background p-4"><p className="whitespace-pre-line text-sm leading-8">{selected.comment}</p></div>
              {selected.status === "PENDING" ? (
                <div className="mt-5 flex flex-wrap gap-3 border-b border-gold/25 pb-5">
                  <button type="button" disabled={pending} onClick={() => void moderate("APPROVED")} className="min-h-11 rounded-full bg-success px-5 text-sm font-black text-white disabled:opacity-60">تأیید نظر</button>
                  <button type="button" disabled={pending} onClick={() => void moderate("REJECTED")} className="min-h-11 rounded-full bg-destructive px-5 text-sm font-black text-white disabled:opacity-60">رد نظر</button>
                </div>
              ) : null}
              <form onSubmit={saveReply} className="mt-5">
                <label htmlFor="store-reply" className="text-sm font-black">پاسخ رسمی فروشگاه</label>
                <textarea id="store-reply" rows={6} maxLength={MAX_STORE_REPLY_LENGTH} value={replyText} onChange={(event) => setReplyText(event.target.value)} disabled={pending} placeholder="پاسخ رسمی و قابل نمایش کنار نظر مشتری را بنویسید." className="mt-2 w-full resize-y rounded-xl border border-border bg-background px-4 py-3 text-sm leading-8 outline-none focus:border-primary disabled:opacity-60" />
                <p className="mt-1 text-xs text-muted-foreground">این پاسخ فقط وقتی نظر تأییدشده باشد در صفحهٔ عمومی نمایش داده می‌شود.</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button disabled={pending} className="min-h-11 rounded-full bg-primary px-5 text-sm font-black text-primary-foreground disabled:opacity-60">{selected.store_reply ? "ذخیرهٔ ویرایش" : "ثبت پاسخ"}</button>
                  {selected.store_reply ? <button type="button" disabled={pending} onClick={() => void deleteReply()} className="min-h-11 rounded-full border border-destructive/30 px-5 text-sm font-bold text-destructive disabled:opacity-60">حذف پاسخ</button> : null}
                </div>
              </form>
            </article>
          ) : (
            <div className="rounded-[1.5rem] border border-gold/35 bg-surface p-10 text-center text-sm text-muted-foreground shadow-card">یک نظر را برای مشاهده و مدیریت انتخاب کنید.</div>
          )}
        </section>
      </div>
    </div>
  );
}
