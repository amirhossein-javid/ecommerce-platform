"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function ManagementSessionBar() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  async function logout() {
    setPending(true);
    try { await fetch("/api/management/auth/logout", { method: "POST" }); }
    finally { router.push("/dashboard"); router.refresh(); }
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gold/35 bg-surface p-4 shadow-card">
      <div><p className="text-sm font-black">نشست اپراتور فعال است</p><p className="text-xs text-muted-foreground">داده‌ها مستقیم از سامانهٔ اصلی و بدون کش مشترک خوانده می‌شوند.</p></div>
      <button type="button" onClick={() => void logout()} disabled={pending} className="min-h-10 rounded-full border border-border px-4 text-sm font-bold hover:bg-background disabled:opacity-60">خروج</button>
    </div>
  );
}
