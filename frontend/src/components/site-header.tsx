import Link from "next/link";

import { Container } from "@/components/container";

const navigation = [
  { href: "/", label: "خانه" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur-sm">
      <Container className="flex min-h-16 items-center justify-between gap-3 py-2 sm:min-h-20">
        <Link
          href="/"
          className="inline-flex min-h-11 items-center rounded-md text-lg font-bold tracking-tight text-foreground sm:text-xl"
          aria-label="صفحهٔ اصلی فروشگاه"
        >
          فروشگاه
        </Link>

        <nav aria-label="ناوبری اصلی">
          <ul className="flex items-center gap-1 sm:gap-2">
            {navigation.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="inline-flex min-h-11 items-center rounded-md px-3 text-sm font-medium text-muted-foreground hover:bg-surface-subtle hover:text-foreground sm:px-4 sm:text-base"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </Container>
    </header>
  );
}
