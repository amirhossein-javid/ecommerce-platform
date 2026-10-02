import Link from "next/link";

import { Container } from "@/components/container";

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <Container className="flex flex-col gap-6 py-8 sm:flex-row sm:items-end sm:justify-between sm:py-10">
        <div className="max-w-md">
          <Link
            href="/"
            className="inline-flex min-h-11 items-center rounded-md text-base font-bold text-foreground"
          >
            فروشگاه
          </Link>
          <p className="mt-1 text-sm leading-7 text-muted-foreground">
            پایهٔ رابط کاربری یک فروشگاه فارسی؛ آماده برای تکمیل در مرحله‌های
            بعد.
          </p>
        </div>

        <nav aria-label="ناوبری پابرگ">
          <ul className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <li>
              <Link className="inline-flex min-h-11 items-center rounded-md" href="/">
                خانه
              </Link>
            </li>
          </ul>
        </nav>
      </Container>
    </footer>
  );
}
