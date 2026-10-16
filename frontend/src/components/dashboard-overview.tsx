"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ManagementLoginCard } from "@/components/management-login-card";
import { ManagementSessionBar } from "@/components/management-session-bar";
import { formatToman } from "@/lib/format-price";
import { isManagementSummary, type ManagementSummary } from "@/lib/management-order-contract";

export function DashboardOverview() {
  const [summary, setSummary] = useState<ManagementSummary | null>(null);
  const [state, setState] = useState<"loading" | "login" | "denied" | "ready" | "error">("loading");

  const load = useCallback(async () => {
    setState("loading");
    try {
      const response = await fetch("/api/management/dashboard", { cache: "no-store" });
      const payload: unknown = await response.json();
      if (response.status === 401) return setState("login");
      if (response.status === 403) return setState("denied");
      if (!response.ok || !isManagementSummary(payload)) return setState("error");
      setSummary(payload);
      setState("ready");
    } catch { setState("error"); }
  }, []);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  if (state === "loading") return <p role="status" className="rounded-2xl border border-gold/35 bg-surface p-8 text-center text-sm text-muted-foreground shadow-card">در حال دریافت نمای عملیات…</p>;
  if (state === "login") return <ManagementLoginCard onAuthenticated={load} />;
  if (state === "denied") return <p role="alert" className="rounded-2xl border border-destructive/25 bg-destructive-soft p-6 text-sm font-bold text-destructive">این حساب مجوز مشاهدهٔ داده‌های سفارش را ندارد. برای مدیریت نظرها می‌توانید از بخش «نظرها» استفاده کنید.</p>;
  if (state === "error" || !summary) return <div className="rounded-2xl border border-destructive/25 bg-destructive-soft p-6 text-sm text-destructive"><p role="alert" className="font-bold">دریافت اطلاعات داشبورد ممکن نشد.</p><button onClick={() => void load()} className="mt-4 min-h-10 rounded-full border border-current px-4 font-bold">تلاش دوباره</button></div>;

  const cards = [
    { label: "همهٔ سفارش‌ها", value: summary.order_count.toLocaleString("fa-IR"), note: "کل سفارش‌های ثبت‌شده" },
    { label: "درآمد پرداخت‌شده", value: formatToman(summary.successful_revenue), note: "سفارش‌های دارای پرداخت موفق" },
    { label: "در انتظار تکمیل", value: summary.pending_fulfillment_count.toLocaleString("fa-IR"), note: "پرداخت‌شده، در پردازش یا ارسال‌شده" },
    { label: "موجودی کم", value: summary.low_stock_product_count.toLocaleString("fa-IR"), note: `محصول فعال با ${summary.low_stock_threshold.toLocaleString("fa-IR")} عدد یا کمتر` },
  ];
  return <div className="space-y-6"><ManagementSessionBar /><section aria-label="شاخص‌های عملیات" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <article key={card.label} className="rounded-[1.35rem] border border-gold/35 bg-surface p-5 shadow-card"><p className="text-sm font-bold text-muted-foreground">{card.label}</p><p className="mt-3 text-2xl font-black text-lapis">{card.value}</p><p className="mt-2 text-xs leading-6 text-muted-foreground">{card.note}</p></article>)}</section><section className="grid gap-4 md:grid-cols-2"><Link href="/dashboard/orders" className="rounded-[1.5rem] border border-primary/25 bg-primary-soft/55 p-6 shadow-card transition hover:border-primary"><span className="text-xs font-black text-primary">عملیات سفارش</span><h2 className="mt-2 text-xl font-black text-lapis">پیگیری و تکمیل سفارش‌ها</h2><p className="mt-2 text-sm leading-7 text-muted-foreground">فیلتر سفارش‌ها، مشاهدهٔ جزئیات و اجرای گام‌های مجاز پردازش و ارسال.</p></Link><Link href="/dashboard/reviews" className="rounded-[1.5rem] border border-gold/40 bg-surface p-6 shadow-card transition hover:border-primary"><span className="text-xs font-black text-primary">صدای مشتری</span><h2 className="mt-2 text-xl font-black text-lapis">نظرها و پاسخ رسمی</h2><p className="mt-2 text-sm leading-7 text-muted-foreground">بررسی نظرهای مشتریان و مدیریت پاسخ رسمی فروشگاه.</p></Link></section></div>;
}
