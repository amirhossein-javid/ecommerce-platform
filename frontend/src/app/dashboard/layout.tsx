import Link from "next/link";
import type { ReactNode } from "react";

import { Container } from "@/components/container";

const navigation = [
  { href: "/dashboard", label: "نمای کلی" },
  { href: "/dashboard/orders", label: "سفارش‌ها" },
  { href: "/dashboard/reviews", label: "نظرها" },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <Container className="py-5 sm:py-8 lg:py-10">
      <header className="naghsh-pattern overflow-hidden rounded-[1.6rem] border border-gold/25 p-5 text-white shadow-card sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div><p className="text-xs font-black text-gold-light">نقش‌جهان · مدیریت فروشگاه</p><h1 className="mt-2 text-2xl font-black sm:text-3xl">داشبورد عملیات</h1><p className="mt-2 max-w-2xl text-sm leading-7 text-white/75">پیگیری سفارش، تکمیل ارسال و رسیدگی به بازخورد مشتریان در یک فضای متمرکز.</p></div>
          <Link href="/" className="inline-flex min-h-11 items-center rounded-full border border-white/30 px-4 text-sm font-bold transition hover:bg-white/10">بازگشت به فروشگاه</Link>
        </div>
      </header>
      <nav aria-label="ناوبری داشبورد" className="my-5 overflow-x-auto rounded-2xl border border-gold/35 bg-surface p-2 shadow-card">
        <ul className="flex min-w-max items-center gap-1">{navigation.map((item) => <li key={item.href}><Link href={item.href} className="inline-flex min-h-11 items-center rounded-xl px-4 text-sm font-black text-lapis transition hover:bg-primary-soft hover:text-primary">{item.label}</Link></li>)}</ul>
      </nav>
      {children}
    </Container>
  );
}
