import Link from "next/link";

import { BrandLogo } from "@/components/brand-logo";
import { Container } from "@/components/container";
import { getCategories } from "@/lib/catalog-api";

export async function SiteFooter() {
  let categories: Awaited<ReturnType<typeof getCategories>> = [];
  try {
    categories = await getCategories();
  } catch {
    // Core footer navigation must remain usable if catalog data is unavailable.
  }

  return (
    <footer className="border-t border-gold/25 bg-lapis-dark text-white">
      <Container className="grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-[1.3fr_1fr_1fr] lg:gap-16 lg:py-16">
        <div className="max-w-md">
          <Link href="/" className="inline-flex min-h-14 items-center" aria-label="صفحهٔ اصلی نقش‌جهان"><BrandLogo inverse /></Link>
          <p className="mt-2 text-sm leading-7 text-white/68">فروشگاه فارسی برای مرور دسته‌بندی‌ها، انتخاب محصول و پیگیری سفارش در یک مسیر یکپارچه.</p>
        </div>
        <nav aria-label="دسترسی‌های فروشگاه">
          <h2 className="text-sm font-black text-gold-light">دسترسی سریع</h2>
          <ul className="mt-3 space-y-1 text-sm text-white/72">
            <li><Link className="inline-flex min-h-10 items-center hover:text-white" href="/products">همهٔ محصولات</Link></li>
            <li><Link className="inline-flex min-h-10 items-center hover:text-white" href="/cart">سبد خرید</Link></li>
            <li><Link className="inline-flex min-h-10 items-center hover:text-white" href="/account">حساب کاربری</Link></li>
            <li><Link className="inline-flex min-h-10 items-center hover:text-white" href="/account/orders">سفارش‌های من</Link></li>
          </ul>
        </nav>
        <nav aria-label="دسته‌بندی‌های فروشگاه">
          <h2 className="text-sm font-black text-gold-light">دسته‌بندی‌ها</h2>
          {categories.length > 0 ? (
            <ul className="mt-3 space-y-1 text-sm text-white/72">
              {categories.slice(0, 4).map((category) => <li key={category.id}><Link className="inline-flex min-h-10 items-center hover:text-white" href={`/products?category=${encodeURIComponent(category.slug)}`}>{category.name}</Link></li>)}
            </ul>
          ) : <p className="mt-4 text-sm leading-7 text-white/55">دسته‌بندی‌ها از کاتالوگ فروشگاه نمایش داده می‌شوند.</p>}
        </nav>
      </Container>
      <div className="border-t border-white/10">
        <Container className="py-5 text-center text-xs text-white/55">© نقش‌جهان — اطلاعات محصولات و قیمت‌ها از کاتالوگ فروشگاه</Container>
      </div>
    </footer>
  );
}
