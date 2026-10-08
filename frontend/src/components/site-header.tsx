import Link from "next/link";

import { Container } from "@/components/container";

const navigation = [
  { href: "/", label: "خانه" },
  { href: "/products", label: "محصولات" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/80 bg-surface/95 backdrop-blur-sm">
      <Container className="flex min-h-[4.75rem] items-center justify-between gap-3 py-2 sm:min-h-20">
        <Link
          href="/"
          className="group inline-flex min-h-11 items-center gap-3 rounded-md"
          aria-label="صفحهٔ اصلی فروشگاه"
        >
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors group-hover:bg-primary-hover sm:size-11">
            <svg
              aria-hidden="true"
              viewBox="0 0 32 32"
              fill="none"
              className="size-6"
            >
              <path
                d="M8 12.5h16l-1 13H9l-1-13Z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinejoin="round"
              />
              <path
                d="M12 13v-2.5a4 4 0 0 1 8 0V13"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-lg font-extrabold tracking-tight text-foreground sm:text-xl">
              فروشگاه
            </span>
            <span className="mt-1.5 hidden text-[0.68rem] font-medium text-muted-foreground sm:block">
              فروشگاه اینترنتی
            </span>
          </span>
        </Link>

        <nav aria-label="ناوبری اصلی">
          <ul className="flex items-center gap-1 sm:gap-2">
            {navigation.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="relative inline-flex min-h-11 items-center rounded-md px-3 text-sm font-semibold text-muted-foreground transition-colors after:absolute after:inset-x-3 after:bottom-1 after:h-px after:origin-center after:scale-x-0 after:bg-primary after:transition-transform hover:bg-primary-soft/55 hover:text-primary hover:after:scale-x-100 sm:px-4 sm:text-[0.95rem]"
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
