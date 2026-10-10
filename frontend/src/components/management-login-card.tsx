"use client";

import { FormEvent, useState } from "react";

export function ManagementLoginCard({ onAuthenticated }: { onAuthenticated: () => void | Promise<void> }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/management/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") }),
      });
      const payload = await response.json() as { error?: unknown };
      if (!response.ok) {
        setError(typeof payload.error === "string" ? payload.error : "ورود به داشبورد ممکن نشد.");
        return;
      }
      await onAuthenticated();
    } catch {
      setError("ارتباط با سرویس ورود برقرار نشد.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-md rounded-[1.5rem] border border-gold/40 bg-surface p-6 shadow-card sm:p-8">
      <h2 className="text-xl font-black">ورود اپراتور</h2>
      <p className="mt-2 text-sm leading-7 text-muted-foreground">ورود مدیریت از حساب مشتری جداست و فقط حساب کارکنان دارای مجوز صریح پذیرفته می‌شود.</p>
      <label htmlFor="management-email" className="mt-6 block text-sm font-bold">ایمیل</label>
      <input id="management-email" name="email" type="email" autoComplete="username" required className="mt-2 min-h-12 w-full rounded-xl border border-border bg-background px-4 outline-none focus:border-primary" />
      <label htmlFor="management-password" className="mt-4 block text-sm font-bold">رمز عبور</label>
      <input id="management-password" name="password" type="password" autoComplete="current-password" required className="mt-2 min-h-12 w-full rounded-xl border border-border bg-background px-4 outline-none focus:border-primary" />
      {error ? <p role="alert" className="mt-4 rounded-xl bg-destructive-soft px-4 py-3 text-sm font-bold text-destructive">{error}</p> : null}
      <button disabled={pending} className="mt-6 min-h-12 w-full rounded-full bg-primary px-5 font-black text-primary-foreground disabled:opacity-60">{pending ? "در حال ورود…" : "ورود به داشبورد"}</button>
    </form>
  );
}
