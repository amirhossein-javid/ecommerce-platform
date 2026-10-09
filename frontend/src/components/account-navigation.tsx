"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

function UserIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      className="size-[1.125rem] shrink-0"
    >
      <path
        d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7 8a7 7 0 0 0-14 0"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AccountNavigation({ label }: { label?: string }) {
  const router = useRouter();
  const lock = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  if (!label) {
    return (
      <Link
        href="/login"
        className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-primary/35 bg-surface px-2.5 text-sm font-bold text-primary shadow-[0_1px_2px_rgb(var(--shadow-color)/0.04)] transition-[color,background-color,border-color,transform] hover:border-primary/60 hover:bg-primary-soft/55 active:scale-[0.98] active:bg-primary-soft sm:px-3"
      >
        <UserIcon />
        <span className="sm:hidden">ورود</span>
        <span className="hidden whitespace-nowrap sm:inline">
          ورود / ثبت‌نام
        </span>
      </Link>
    );
  }

  const logout = async () => {
    if (lock.current) return;
    lock.current = true;
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!response.ok) {
        setError("خروج از حساب ممکن نشد.");
        return;
      }
      router.push("/");
      router.refresh();
    } catch {
      setError("ارتباط برقرار نشد؛ دوباره تلاش کنید.");
    } finally {
      lock.current = false;
      setPending(false);
    }
  };

  return (
    <div className="relative flex min-h-11 items-center overflow-visible rounded-lg border border-primary/30 bg-surface text-primary shadow-[0_1px_2px_rgb(var(--shadow-color)/0.04)] transition-colors hover:border-primary/55 hover:bg-primary-soft/35">
      <span
        className="inline-flex min-h-11 items-center gap-1.5 px-2.5"
        title={label}
      >
        <UserIcon />
        <span className="hidden max-w-28 truncate text-sm font-bold md:inline">
          {label}
        </span>
      </span>
      <span className="h-5 w-px bg-border" aria-hidden="true" />
      <button
        type="button"
        onClick={logout}
        disabled={pending}
        className="inline-flex min-h-11 items-center rounded-e-lg px-2.5 text-sm font-bold text-primary transition-[color,background-color,transform] hover:bg-primary-soft/70 active:scale-[0.97] active:bg-primary-soft disabled:cursor-wait disabled:opacity-60 sm:px-3"
      >
        {pending ? "…" : "خروج"}
      </button>
      {error ? (
        <span
          className="absolute end-0 top-full z-40 mt-1 w-56 rounded-lg bg-destructive-soft px-3 py-2 text-xs font-semibold leading-6 text-destructive shadow-card"
          role="alert"
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}
