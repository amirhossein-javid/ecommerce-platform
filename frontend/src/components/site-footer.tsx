import Link from "next/link";

import { Container } from "@/components/container";

export function SiteFooter() {
  return (
    <footer className="border-t border-primary/10 bg-primary text-primary-foreground">
      <Container className="flex flex-col gap-7 py-9 sm:flex-row sm:items-end sm:justify-between sm:py-11">
        <div className="max-w-md">
          <Link
            href="/"
            className="inline-flex min-h-11 items-center rounded-md text-lg font-extrabold"
          >
            فروشگاه
          </Link>
          <p className="mt-1 max-w-sm text-sm leading-7 text-primary-foreground/70">
            تجربه‌ای فارسی، روشن و منسجم برای مرور محصولات فروشگاه.
          </p>
        </div>

        <nav aria-label="ناوبری پابرگ">
          <ul className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm font-semibold text-primary-foreground/75">
            <li>
              <Link
                className="inline-flex min-h-11 items-center rounded-md transition-colors hover:text-primary-foreground"
                href="/"
              >
                خانه
              </Link>
            </li>
            <li>
              <Link
                className="inline-flex min-h-11 items-center rounded-md transition-colors hover:text-primary-foreground"
                href="/products"
              >
                محصولات
              </Link>
            </li>
          </ul>
        </nav>
      </Container>
    </footer>
  );
}
