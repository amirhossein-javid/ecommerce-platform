"use client";

import { type ReactNode, useRef } from "react";

type MobileFilterDrawerProps = {
  activeCount: number;
  children: ReactNode;
};

export function MobileFilterDrawer({
  activeCount,
  children,
}: MobileFilterDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  return (
    <div className="lg:hidden">
      <button
        type="button"
        onClick={() => dialogRef.current?.showModal()}
        aria-haspopup="dialog"
        className="inline-flex min-h-11 items-center gap-2 rounded-full border border-gold/40 bg-background px-4 text-sm font-bold text-foreground transition-colors hover:bg-primary-soft hover:text-primary"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          className="size-5"
        >
          <path
            d="M4 7h16M7 12h10M10 17h4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
        فیلترها
        {activeCount > 0 ? (
          <span className="grid min-w-6 place-items-center rounded-full bg-primary px-1.5 py-0.5 text-[0.68rem] text-primary-foreground">
            {activeCount.toLocaleString("fa-IR")}
          </span>
        ) : null}
      </button>

      <dialog
        ref={dialogRef}
        aria-labelledby="mobile-filter-title"
        className="fixed inset-y-0 right-0 m-0 h-dvh max-h-none w-[min(88vw,22rem)] max-w-none overflow-hidden border-0 bg-surface p-0 text-foreground shadow-card backdrop:bg-lapis-dark/55"
      >
        <div className="flex h-full flex-col">
          <header className="naghsh-pattern relative flex min-h-20 items-center justify-between border-b border-gold/50 px-4 text-white">
            <div className="absolute inset-0 bg-lapis-dark/80" aria-hidden="true" />
            <h2 id="mobile-filter-title" className="relative text-lg font-extrabold text-white">
              فیلتر محصولات
            </h2>
            <form method="dialog">
              <button
                type="submit"
                className="relative grid size-11 place-items-center rounded-full border border-gold/45 text-2xl text-white transition-colors hover:bg-white/10"
                aria-label="بستن فیلترها"
              >
                <span aria-hidden="true">×</span>
              </button>
            </form>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            <h3 className="mb-3 text-sm font-extrabold text-primary">
              دسته‌بندی
            </h3>
            {children}
          </div>
        </div>
      </dialog>
    </div>
  );
}
