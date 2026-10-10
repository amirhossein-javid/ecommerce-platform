"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";

import { AccountNavigation, type AccountNavigationState } from "@/components/account-navigation";

const navigation = [
  { href: "/#top", label: "خانه" },
  { href: "/#categories", label: "دسته‌بندی‌ها" },
  { href: "/products", label: "محصولات" },
  { href: "/#heritage", label: "میراث ما" },
] as const;

type MobileNavigationProps = {
  accountLabel?: string;
  accountState: AccountNavigationState;
};

export function MobileNavigation({ accountLabel, accountState }: MobileNavigationProps) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const isCustomer = accountState === "customer";

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <div className="lg:hidden">
      <button
        type="button"
        aria-label={open ? "بستن منوی اصلی" : "باز کردن منوی اصلی"}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((current) => !current)}
        className="grid size-11 place-items-center rounded-full border border-gold/65 bg-surface text-primary transition hover:border-gold hover:bg-gold-light/20 active:scale-[0.97]"
      >
        <span className="relative block h-4 w-5" aria-hidden="true">
          <span className={`absolute start-0 top-0 h-0.5 w-5 rounded bg-current transition-transform ${open ? "translate-y-[7px] rotate-45" : ""}`} />
          <span className={`absolute start-0 top-[7px] h-0.5 w-5 rounded bg-current transition-opacity ${open ? "opacity-0" : ""}`} />
          <span className={`absolute start-0 top-[14px] h-0.5 w-5 rounded bg-current transition-transform ${open ? "-translate-y-[7px] -rotate-45" : ""}`} />
        </span>
      </button>

      {open ? (
        <div id={menuId} className="absolute inset-x-0 top-full border-t border-gold/30 bg-background shadow-[0_22px_45px_-24px_rgb(var(--shadow-color)/0.55)]">
          <nav className="mx-auto max-w-7xl px-4 py-4 sm:px-6" aria-label="منوی اصلی موبایل">
            <ul className="grid grid-cols-2 gap-2">
              {navigation.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} onClick={() => setOpen(false)} className="flex min-h-12 items-center justify-between rounded-xl border border-gold/25 bg-surface px-4 text-sm font-black text-foreground transition hover:border-gold/65 hover:text-primary">
                    {item.label}<span className="text-gold" aria-hidden="true">←</span>
                  </Link>
                </li>
              ))}
              {isCustomer ? (
                <>
                  <li><Link href="/account" onClick={() => setOpen(false)} className="flex min-h-12 items-center rounded-xl border border-gold/25 bg-surface px-4 text-sm font-black text-foreground hover:border-gold/65 hover:text-primary">حساب کاربری</Link></li>
                  <li><Link href="/account/orders" onClick={() => setOpen(false)} className="flex min-h-12 items-center rounded-xl border border-gold/25 bg-surface px-4 text-sm font-black text-foreground hover:border-gold/65 hover:text-primary">سفارش‌های من</Link></li>
                </>
              ) : null}
            </ul>
            <div className="mt-3 flex items-center justify-between gap-3 border-t border-gold/25 pt-3" onClick={() => setOpen(false)}>
              <p className="text-xs font-bold text-muted-foreground">{isCustomer ? "مدیریت نشست حساب" : "برای خرید و پیگیری سفارش"}</p>
              <AccountNavigation state={accountState} label={accountLabel} />
            </div>
          </nav>
        </div>
      ) : null}
    </div>
  );
}
