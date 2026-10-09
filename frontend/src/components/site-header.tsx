import Link from "next/link";

import { AccountNavigation } from "@/components/account-navigation";
import { Container } from "@/components/container";
import { getCurrentCustomer } from "@/lib/auth-session";
import { getCurrentGuestCart } from "@/lib/cart-api";
import { getCartItemCount } from "@/lib/cart-contract";

const navigation = [
  { href: "/", label: "خانه" },
  { href: "/products", label: "محصولات" },
];

export async function SiteHeader() {
  let cartItemCount = 0;
  const customer = await getCurrentCustomer();

  try {
    cartItemCount = getCartItemCount(await getCurrentGuestCart());
  } catch {
    // Keep global navigation available when the cart service is temporarily down.
  }

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
              <li
                key={item.href}
                className={item.href === "/" ? "hidden sm:block" : undefined}
              >
                <Link
                  href={item.href}
                  className="relative inline-flex min-h-11 items-center rounded-md px-3 text-sm font-semibold text-muted-foreground transition-colors after:absolute after:inset-x-3 after:bottom-1 after:h-px after:origin-center after:scale-x-0 after:bg-primary after:transition-transform hover:bg-primary-soft/55 hover:text-primary hover:after:scale-x-100 sm:px-4 sm:text-[0.95rem]"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                href="/cart"
                aria-label={`سبد خرید، ${cartItemCount.toLocaleString("fa-IR")} کالا`}
                className="relative inline-flex min-h-11 min-w-11 items-center justify-center gap-1.5 rounded-lg border border-primary/15 bg-primary-soft/60 px-2.5 text-sm font-bold text-primary transition-[color,background-color,border-color,transform] hover:border-primary/35 hover:bg-primary-soft active:scale-[0.98] active:bg-primary-soft sm:gap-2 sm:px-3 sm:text-[0.95rem]"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  className="size-5 shrink-0"
                >
                  <path
                    d="M4 5h2l1.5 9h9.75l1.5-6H7M10 18.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm8 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                {cartItemCount > 0 ? (
                  <span className="grid min-w-5 place-items-center rounded-full bg-primary px-1.5 py-0.5 text-[0.65rem] font-black leading-4 text-primary-foreground shadow-[0_1px_2px_rgb(var(--shadow-color)/0.12)]">
                    {cartItemCount.toLocaleString("fa-IR")}
                  </span>
                ) : null}
              </Link>
            </li>
            <li>
              <AccountNavigation
                label={
                  customer
                    ? customer.first_name || customer.email
                    : undefined
                }
              />
            </li>
          </ul>
        </nav>
      </Container>
    </header>
  );
}
