import Link from "next/link";

import { AccountNavigation } from "@/components/account-navigation";
import { BrandLogo } from "@/components/brand-logo";
import { Container } from "@/components/container";
import { MobileNavigation } from "@/components/mobile-navigation";
import { getCustomerSession } from "@/lib/auth-session";
import { getCurrentCart } from "@/lib/cart-api";
import { getCartItemCount } from "@/lib/cart-contract";

const navigation = [
  { href: "/#top", label: "خانه" },
  { href: "/#categories", label: "دسته‌بندی‌ها" },
  { href: "/products", label: "محصولات" },
  { href: "/#heritage", label: "میراث ما" },
];

export async function SiteHeader() {
  let cartItemCount = 0;
  const session = await getCustomerSession();

  try {
    cartItemCount = getCartItemCount(await getCurrentCart());
  } catch {
    // Keep global navigation available when the cart service is temporarily down.
  }

  return (
    <header id="top" className="sticky top-0 z-30 scroll-mt-0 border-b border-gold/35 bg-background/95 shadow-[0_8px_24px_-22px_rgb(var(--shadow-color)/0.55)] backdrop-blur-md">
      <Container className="flex min-h-[4.75rem] items-center justify-between gap-3 py-2 sm:min-h-[5.25rem]">
        <Link href="/#top" className="group inline-flex min-h-11 items-center gap-2.5 rounded-md" aria-label="صفحهٔ اصلی نقش‌جهان">
          <BrandLogo />
        </Link>

        <nav className="hidden lg:block" aria-label="ناوبری اصلی">
          <ul className="flex items-center gap-1">
            {navigation.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="relative inline-flex min-h-11 items-center rounded-full px-4 text-sm font-bold text-foreground transition-colors after:absolute after:inset-x-4 after:bottom-1 after:h-px after:origin-center after:scale-x-0 after:bg-gold after:transition-transform hover:text-primary hover:after:scale-x-100">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <nav aria-label="سبد خرید و حساب کاربری">
          <ul className="flex items-center gap-2">
            <li>
              <Link href="/cart" aria-label={`سبد خرید، ${cartItemCount.toLocaleString("fa-IR")} کالا`} className="relative inline-flex min-h-11 min-w-11 items-center justify-center rounded-full border border-gold/65 bg-surface text-primary transition-[background-color,border-color,transform] hover:border-gold hover:bg-gold-light/20 active:scale-[0.97]">
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="size-5 shrink-0"><path d="M4 5h2l1.5 9h9.75l1.5-6H7M10 18.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm8 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                {cartItemCount > 0 ? <span className="absolute -end-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-lapis px-1 text-[0.62rem] font-black leading-none text-white">{cartItemCount.toLocaleString("fa-IR")}</span> : null}
              </Link>
            </li>
            <li className="hidden lg:block"><AccountNavigation state={session.state} label={session.state === "customer" ? session.customer.first_name || session.customer.email : undefined} /></li>
            <li><MobileNavigation accountState={session.state} accountLabel={session.state === "customer" ? session.customer.first_name || session.customer.email : undefined} /></li>
          </ul>
        </nav>
      </Container>
    </header>
  );
}
