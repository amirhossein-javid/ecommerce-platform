"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { ManagementLoginCard } from "@/components/management-login-card";
import { ManagementSessionBar } from "@/components/management-session-bar";
import { OrderStatusBadge } from "@/components/order-status-badge";
import { formatToman } from "@/lib/format-price";
import {
  isManagementOrderDetail,
  isManagementOrderPage,
  type ManagementOrderDetail,
  type ManagementOrderPage,
} from "@/lib/management-order-contract";
import { ORDER_STATUS_LABELS } from "@/lib/order-policy";

const statuses = Object.entries(ORDER_STATUS_LABELS);

function date(value: string | null) {
  return value ? new Intl.DateTimeFormat("fa-IR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
}

function errorText(value: unknown, fallback: string) {
  return value && typeof value === "object" && "error" in value && typeof value.error === "string" ? value.error : fallback;
}

export function OrderManagementPanel() {
  const [state, setState] = useState<"loading" | "login" | "denied" | "ready">("loading");
  const [page, setPage] = useState<ManagementOrderPage | null>(null);
  const [selected, setSelected] = useState<ManagementOrderDetail | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [applied, setApplied] = useState({ search: "", status: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadDetail = useCallback(async (id: number) => {
    setBusy(true); setError("");
    try {
      const response = await fetch(`/api/management/orders/${id}`, { cache: "no-store" });
      const payload: unknown = await response.json();
      if (response.status === 401) { setState("login"); setSelected(null); return; }
      if (response.status === 403) { setState("denied"); setSelected(null); return; }
      if (!response.ok || !isManagementOrderDetail(payload)) { setError(errorText(payload, "دریافت جزئیات سفارش ممکن نشد.")); return; }
      setSelected(payload);
    } catch { setError("ارتباط با سرویس سفارش برقرار نشد."); }
    finally { setBusy(false); }
  }, []);

  const loadOrders = useCallback(async (requestedPage = 1, filters = { search: "", status: "" }) => {
    setState("loading"); setError("");
    const query = new URLSearchParams();
    if (filters.search) query.set("search", filters.search);
    if (filters.status) query.set("status", filters.status);
    if (requestedPage > 1) query.set("page", String(requestedPage));
    try {
      const response = await fetch(`/api/management/orders?${query}`, { cache: "no-store" });
      const payload: unknown = await response.json();
      if (response.status === 401) return setState("login");
      if (response.status === 403) return setState("denied");
      if (!response.ok || !isManagementOrderPage(payload)) { setError(errorText(payload, "دریافت فهرست سفارش‌ها ممکن نشد.")); setState("ready"); return; }
      setPage(payload); setCurrentPage(requestedPage); setState("ready");
      const nextId = payload.results[0]?.id;
      if (nextId) await loadDetail(nextId); else setSelected(null);
    } catch { setError("ارتباط با سرویس سفارش برقرار نشد."); setState("ready"); }
  }, [loadDetail]);

  useEffect(() => { const timer = window.setTimeout(() => void loadOrders(), 0); return () => window.clearTimeout(timer); }, [loadOrders]);

  async function mutate(path: string, init: RequestInit, success: string) {
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch(`/api/management/orders/${selected.id}/${path}`, init);
      const payload: unknown = await response.json();
      if (!response.ok || !isManagementOrderDetail(payload)) { setError(errorText(payload, "انجام عملیات سفارش ممکن نشد.")); return; }
      setSelected(payload); setNotice(success);
      await loadOrders(currentPage, applied);
      await loadDetail(payload.id);
    } catch { setError("ارتباط با سرویس سفارش برقرار نشد."); }
    finally { setBusy(false); }
  }

  function filter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const filters = { search: search.trim(), status };
    setApplied(filters); void loadOrders(1, filters);
  }

  function saveShipment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    void mutate("shipment", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ carrier: form.get("carrier"), tracking_number: form.get("tracking_number") }) }, "اطلاعات مرسوله ذخیره شد.");
  }

  if (state === "loading" && !page) return <p role="status" className="rounded-2xl border border-gold/35 bg-surface p-8 text-center text-sm text-muted-foreground shadow-card">در حال دریافت سفارش‌ها…</p>;
  if (state === "login") return <ManagementLoginCard onAuthenticated={() => loadOrders()} />;
  if (state === "denied") return <p role="alert" className="rounded-2xl border border-destructive/25 bg-destructive-soft p-6 text-sm font-bold text-destructive">مجوز مشاهده یا تغییر سفارش‌ها برای این حساب فعال نیست.</p>;

  return <div className="space-y-5">
    <ManagementSessionBar />
    <form onSubmit={filter} className="grid gap-3 rounded-2xl border border-gold/35 bg-surface p-4 shadow-card sm:grid-cols-[1fr_14rem_auto]">
      <input value={search} onChange={(event) => setSearch(event.target.value)} maxLength={255} placeholder="شناسه، نام یا ایمیل مشتری" className="min-h-11 rounded-xl border border-border bg-background px-4 text-sm outline-none focus:border-primary" />
      <select value={status} onChange={(event) => setStatus(event.target.value)} className="min-h-11 rounded-xl border border-border bg-background px-3 text-sm"><option value="">همهٔ وضعیت‌ها</option>{statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <button disabled={busy} className="min-h-11 rounded-full bg-lapis px-5 text-sm font-black text-white disabled:opacity-60">اعمال فیلتر</button>
    </form>
    {error ? <p role="alert" className="rounded-xl border border-destructive/20 bg-destructive-soft px-4 py-3 text-sm font-bold text-destructive">{error}</p> : null}
    {notice ? <p role="status" className="rounded-xl border border-success/20 bg-success-soft px-4 py-3 text-sm font-bold text-success">{notice}</p> : null}
    <div className="grid gap-5 xl:grid-cols-[minmax(19rem,0.78fr)_minmax(0,1.35fr)] xl:items-start">
      <section aria-label="فهرست سفارش‌ها" className="space-y-3">
        <p className="px-1 text-sm font-bold text-muted-foreground">{page?.count.toLocaleString("fa-IR") ?? "۰"} سفارش</p>
        {page?.results.map((order) => <button key={order.id} type="button" onClick={() => void loadDetail(order.id)} className={`w-full rounded-2xl border p-4 text-start shadow-card transition ${selected?.id === order.id ? "border-primary bg-primary-soft/45" : "border-gold/35 bg-surface hover:border-primary/45"}`}><div className="flex items-center justify-between gap-2"><strong>سفارش {order.id.toLocaleString("fa-IR")}</strong><OrderStatusBadge status={order.status} /></div><p className="mt-2 text-sm font-bold">{order.customer_display_name}</p><div className="mt-3 flex items-end justify-between gap-2 text-xs text-muted-foreground"><span>{order.item_count.toLocaleString("fa-IR")} قلم</span><span className="font-black text-foreground">{formatToman(order.grand_total)}</span></div></button>)}
        {!busy && page?.results.length === 0 ? <p className="rounded-2xl border border-gold/35 bg-surface p-8 text-center text-sm text-muted-foreground">سفارشی مطابق فیلترها پیدا نشد.</p> : null}
        <div className="flex items-center justify-between gap-3"><button disabled={!page?.previous || busy} onClick={() => void loadOrders(currentPage - 1, applied)} className="min-h-10 rounded-full border border-border px-4 text-sm font-bold disabled:opacity-40">صفحهٔ قبل</button><span className="text-xs text-muted-foreground">صفحهٔ {currentPage.toLocaleString("fa-IR")}</span><button disabled={!page?.next || busy} onClick={() => void loadOrders(currentPage + 1, applied)} className="min-h-10 rounded-full border border-border px-4 text-sm font-bold disabled:opacity-40">صفحهٔ بعد</button></div>
      </section>
      <section aria-label="جزئیات سفارش" className="xl:sticky xl:top-28">
        {selected ? <OrderDetail order={selected} busy={busy} mutate={mutate} saveShipment={saveShipment} /> : <div className="rounded-[1.5rem] border border-gold/35 bg-surface p-10 text-center text-sm text-muted-foreground shadow-card">یک سفارش را برای مشاهده انتخاب کنید.</div>}
      </section>
    </div>
  </div>;
}

function OrderDetail({ order, busy, mutate, saveShipment }: { order: ManagementOrderDetail; busy: boolean; mutate: (path: string, init: RequestInit, success: string) => Promise<void>; saveShipment: (event: FormEvent<HTMLFormElement>) => void }) {
  const next = order.status === "PAID" ? "PROCESSING" : order.status === "PROCESSING" ? "SHIPPED" : order.status === "SHIPPED" ? "DELIVERED" : null;
  const cancellable = ["PENDING_PAYMENT", "PAID", "PROCESSING"].includes(order.status);
  return <article className="max-h-[calc(100dvh-8rem)] overflow-y-auto rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card sm:p-7">
    <header className="flex flex-wrap items-start justify-between gap-3 border-b border-gold/25 pb-5"><div><p className="text-xs font-black text-primary">سفارش {order.id.toLocaleString("fa-IR")}</p><h2 className="mt-1 text-xl font-black text-lapis">{order.customer_display_name}</h2><p className="text-xs text-muted-foreground" dir="ltr">{order.customer_email}</p></div><OrderStatusBadge status={order.status} /></header>
    <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-3"><div><dt className="text-muted-foreground">مبلغ نهایی</dt><dd className="font-black">{formatToman(order.grand_total)}</dd></div><div><dt className="text-muted-foreground">ثبت سفارش</dt><dd className="font-bold">{date(order.created_at)}</dd></div><div><dt className="text-muted-foreground">وضعیت بازپرداخت</dt><dd className="font-bold">{{ NOT_REQUIRED: "لازم نیست", REQUIRED: "نیازمند اقدام", RESOLVED: "انجام‌شده" }[order.refund_status]}</dd></div></dl>
    <section className="mt-6"><h3 className="font-black">اقلام سفارش</h3><div className="mt-3 divide-y divide-gold/20 rounded-xl bg-background px-4">{order.items.map((item) => <div key={item.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm"><span><strong>{item.product_name}</strong><small className="block text-muted-foreground" dir="ltr">{item.sku}</small></span><span>{item.quantity.toLocaleString("fa-IR")} × {formatToman(item.unit_price)}</span></div>)}</div></section>
    <section className="mt-6"><h3 className="font-black">نشانی تحویل</h3><p className="mt-2 rounded-xl bg-background p-4 text-sm leading-7">{order.shipping_recipient_first_name} {order.shipping_recipient_last_name}، {order.shipping_province}، {order.shipping_city}، {order.shipping_address}<br /><span dir="ltr">{order.shipping_recipient_phone_number}</span> · کدپستی {order.shipping_postal_code}</p></section>
    {order.status === "PROCESSING" ? <form onSubmit={saveShipment} className="mt-6 rounded-xl border border-primary/20 bg-primary-soft/35 p-4"><h3 className="font-black">اطلاعات مرسوله</h3><div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="text-sm font-bold">حامل<input name="carrier" required maxLength={100} defaultValue={order.shipment?.carrier ?? ""} className="mt-1 min-h-11 w-full rounded-lg border border-border bg-surface px-3 font-normal" /></label><label className="text-sm font-bold">کد رهگیری<input name="tracking_number" required maxLength={255} defaultValue={order.shipment?.tracking_number ?? ""} className="mt-1 min-h-11 w-full rounded-lg border border-border bg-surface px-3 font-normal" /></label></div><button disabled={busy} className="mt-3 min-h-10 rounded-full bg-primary px-4 text-sm font-black text-white disabled:opacity-50">ذخیرهٔ مرسوله</button></form> : null}
    <section className="mt-6 border-t border-gold/25 pt-5"><h3 className="font-black">عملیات مجاز</h3><div className="mt-3 flex flex-wrap gap-3">{next ? <button disabled={busy || (next === "SHIPPED" && (!order.shipment?.carrier || !order.shipment.tracking_number))} onClick={() => void mutate("transition", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: next }) }, `وضعیت سفارش به «${ORDER_STATUS_LABELS[next]}» تغییر کرد.`)} className="min-h-11 rounded-full bg-primary px-5 text-sm font-black text-white disabled:opacity-45">{ORDER_STATUS_LABELS[next]}</button> : null}{cancellable ? <button disabled={busy} onClick={() => window.confirm("این سفارش لغو شود؟") && void mutate("transition", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "CANCELLED" }) }, "سفارش لغو شد.")} className="min-h-11 rounded-full border border-destructive/35 px-5 text-sm font-bold text-destructive disabled:opacity-45">لغو سفارش</button> : null}{order.refund_status === "REQUIRED" ? <button disabled={busy} onClick={() => window.confirm("انجام بازپرداخت به‌صورت دستی تأیید شود؟") && void mutate("resolve-refund", { method: "POST" }, "بازپرداخت انجام‌شده ثبت شد.")} className="min-h-11 rounded-full bg-lapis px-5 text-sm font-black text-white disabled:opacity-45">ثبت انجام بازپرداخت</button> : null}</div></section>
    <section className="mt-6"><h3 className="font-black">تاریخچهٔ وضعیت</h3>{order.status_history.length ? <ol className="mt-3 space-y-2">{order.status_history.map((entry, index) => <li key={`${entry.created_at}-${index}`} className="rounded-xl border border-gold/25 px-4 py-3 text-sm"><div className="flex flex-wrap justify-between gap-2"><strong>{ORDER_STATUS_LABELS[entry.from_status]} ← {ORDER_STATUS_LABELS[entry.to_status]}</strong><time className="text-xs text-muted-foreground">{date(entry.created_at)}</time></div><p className="mt-1 text-xs text-muted-foreground">{entry.actor_type === "SYSTEM" ? "سامانه" : entry.actor_type === "OPERATOR" ? `اپراتور${entry.actor_display_name ? `: ${entry.actor_display_name}` : ""}` : "مشتری"}</p></li>)}</ol> : <p className="mt-2 text-sm text-muted-foreground">هنوز تغییری ثبت نشده است.</p>}</section>
  </article>;
}
