import Link from "next/link";

import { MobileFilterDrawer } from "@/components/mobile-filter-drawer";
import type { Category } from "@/lib/catalog-api";
import {
  catalogHref,
  type CatalogQuery,
  DEFAULT_PRODUCT_ORDERING,
  MAX_CATALOG_SEARCH_LENGTH,
  type ProductOrdering,
} from "@/lib/catalog-query";

type CatalogControlsProps = {
  categories: Category[];
  categoriesUnavailable: boolean;
  query: CatalogQuery;
  resultCount: number;
};

const ORDERING_OPTIONS: Array<{ value: ProductOrdering; label: string }> = [
  { value: "-created_at", label: "جدیدترین" },
  { value: "created_at", label: "قدیمی‌ترین" },
  { value: "price", label: "کمترین قیمت" },
  { value: "-price", label: "بیشترین قیمت" },
];

function CategoryLinks({
  categories,
  categoriesUnavailable,
  query,
}: Omit<CatalogControlsProps, "resultCount">) {
  if (categoriesUnavailable) {
    return (
      <p className="rounded-xl border border-gold/25 bg-background px-3 py-4 text-sm leading-7 text-muted-foreground">
        دسته‌بندی‌ها موقتاً در دسترس نیستند. جست‌وجو و مرتب‌سازی همچنان قابل
        استفاده است.
      </p>
    );
  }

  const linkClasses =
    "flex min-h-11 items-center justify-between gap-3 rounded-xl px-3 py-2 text-sm font-semibold transition-colors";

  return (
    <nav aria-label="فیلتر دسته‌بندی">
      <ul className="space-y-1">
        <li>
          <Link
            href={catalogHref(query, { category: "", page: 1 })}
            aria-current={query.category ? undefined : "page"}
            className={`${linkClasses} ${
              query.category
                ? "text-muted-foreground hover:bg-background hover:text-primary"
                : "bg-primary text-primary-foreground shadow-sm"
            }`}
          >
            همهٔ محصولات
          </Link>
        </li>
        {categories.map((category) => {
          const isActive = category.slug === query.category;

          return (
            <li key={category.id}>
              <Link
                href={catalogHref(query, {
                  category: category.slug,
                  page: 1,
                })}
                aria-current={isActive ? "page" : undefined}
                className={`${linkClasses} ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-background hover:text-primary"
                }`}
              >
                <span className="min-w-0 truncate">{category.name}</span>
                {category.parent ? (
                  <span
                    className={`shrink-0 text-[0.68rem] ${
                      isActive
                        ? "text-primary-foreground/70"
                        : "text-muted-foreground/75"
                    }`}
                  >
                    {category.parent.name}
                  </span>
                ) : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function CatalogDiscovery({
  categories,
  query,
}: Pick<CatalogControlsProps, "categories" | "query">) {
  const selectedCategory = categories.find(
    (category) => category.slug === query.category,
  );
  const selectedOrdering = ORDERING_OPTIONS.find(
    (option) => option.value === query.ordering,
  );
  const hasDiscoveryState = Boolean(
    query.search || query.category || query.ordering !== DEFAULT_PRODUCT_ORDERING,
  );
  const activeItems = [
    query.search
      ? {
          key: "search",
          label: `جست‌وجو: ${query.search}`,
          href: catalogHref(query, { search: "", page: 1 }),
        }
      : null,
    query.category
      ? {
          key: "category",
          label: selectedCategory?.name ?? query.category,
          href: catalogHref(query, { category: "", page: 1 }),
        }
      : null,
    query.ordering !== DEFAULT_PRODUCT_ORDERING
      ? {
          key: "ordering",
          label: selectedOrdering?.label ?? "مرتب‌سازی",
          href: catalogHref(query, {
            ordering: DEFAULT_PRODUCT_ORDERING,
            page: 1,
          }),
        }
      : null,
  ].filter((item): item is NonNullable<typeof item> => item !== null);

  return (
    <section aria-labelledby="catalog-discovery-title" className="mt-6 sm:mt-8">
      <h2 id="catalog-discovery-title" className="sr-only">
        جست‌وجوی محصولات
      </h2>

      <div className="mx-auto max-w-4xl rounded-[1.5rem] border border-gold/45 bg-surface p-2 shadow-card sm:p-2.5">
        <form action="/products" method="get" role="search">
          {query.category ? (
            <input type="hidden" name="category" value={query.category} />
          ) : null}
          {query.ordering !== DEFAULT_PRODUCT_ORDERING ? (
            <input type="hidden" name="ordering" value={query.ordering} />
          ) : null}
          <label htmlFor="catalog-search" className="sr-only">
            جست‌وجوی محصولات
          </label>
          <div className="flex min-w-0 flex-col gap-2 min-[430px]:flex-row">
            <div className="relative min-w-0 flex-1">
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 start-3.5 grid place-items-center text-muted-foreground"
              >
                <svg viewBox="0 0 24 24" fill="none" className="size-5">
                  <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.8" />
                  <path d="m16 16 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </span>
              <input
                id="catalog-search"
                type="search"
                name="search"
                defaultValue={query.search}
                maxLength={MAX_CATALOG_SEARCH_LENGTH}
                placeholder="جست‌وجو در محصولات"
                enterKeyHint="search"
                className="catalog-search-field min-h-12 w-full min-w-0 rounded-full border border-transparent bg-background ps-11 pe-4 text-sm font-semibold text-foreground transition-colors placeholder:text-muted-foreground/80 hover:border-gold/55 focus:border-primary sm:text-base"
              />
            </div>
            <button
              type="submit"
              className="min-h-12 shrink-0 rounded-full bg-primary px-6 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover sm:px-8"
            >
              جست‌وجو
            </button>
          </div>
        </form>
      </div>

      {hasDiscoveryState ? (
        <div className="mt-3 flex min-w-0 flex-wrap items-center justify-between gap-2">
          <ul
            aria-label="انتخاب‌های فعال"
            className="flex min-w-0 flex-wrap gap-2"
          >
            {activeItems.map((item) => (
              <li key={item.key} className="min-w-0 max-w-full">
                <Link
                  href={item.href}
                  aria-label={`حذف ${item.label}`}
                  className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-full border border-primary/15 bg-primary-soft/70 px-3 text-xs font-bold text-primary transition-colors hover:bg-primary-soft"
                >
                  <span className="truncate">{item.label}</span>
                  <span aria-hidden="true" className="text-base leading-none">
                    ×
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <Link
            href="/products"
            className="inline-flex min-h-10 w-fit items-center rounded-full px-3 text-sm font-bold text-primary transition-colors hover:bg-primary-soft/65"
          >
            پاک‌کردن همه
          </Link>
        </div>
      ) : null}
    </section>
  );
}

export function CatalogSidebar({
  categories,
  categoriesUnavailable,
  query,
}: Omit<CatalogControlsProps, "resultCount">) {
  return (
    <aside aria-labelledby="catalog-sidebar-title" className="hidden lg:block">
      <div className="sticky top-24 rounded-[1.5rem] border border-gold/40 bg-surface p-4 shadow-card">
        <div className="mb-4 flex min-h-10 items-center justify-between border-b border-gold/30 pb-3">
          <h2
            id="catalog-sidebar-title"
            className="text-base font-extrabold text-foreground"
          >
            دسته‌بندی‌ها
          </h2>
          {query.category ? (
            <Link
              href={catalogHref(query, { category: "", page: 1 })}
              className="rounded-full px-3 py-1 text-xs font-bold text-primary transition-colors hover:bg-primary-soft"
            >
              پاک‌کردن
            </Link>
          ) : null}
        </div>
        <CategoryLinks
          categories={categories}
          categoriesUnavailable={categoriesUnavailable}
          query={query}
        />
      </div>
    </aside>
  );
}

export function CatalogToolbar({
  categories,
  categoriesUnavailable,
  query,
  resultCount,
}: CatalogControlsProps) {
  return (
    <div className="flex min-w-0 flex-col gap-3 rounded-[1.25rem] border border-gold/35 bg-surface px-3 py-3 shadow-[0_12px_28px_-26px_rgb(var(--shadow-color)/0.4)] sm:flex-row sm:items-center sm:justify-between sm:px-4">
      <div className="flex min-w-0 items-center gap-3">
        <MobileFilterDrawer activeCount={Number(Boolean(query.category))}>
          <CategoryLinks
            categories={categories}
            categoriesUnavailable={categoriesUnavailable}
            query={query}
          />
        </MobileFilterDrawer>
        <p className="shrink-0 text-sm text-muted-foreground" aria-live="polite">
          <strong className="font-black text-foreground">
            {resultCount.toLocaleString("fa-IR")}
          </strong>{" "}
          محصول
        </p>
      </div>

      <form
        action="/products"
        method="get"
        aria-label="مرتب‌سازی محصولات"
        className="flex min-w-0 items-center gap-2 lg:hidden"
      >
        {query.search ? (
          <input type="hidden" name="search" value={query.search} />
        ) : null}
        {query.category ? (
          <input type="hidden" name="category" value={query.category} />
        ) : null}
        <label
          htmlFor="mobile-ordering"
          className="shrink-0 text-xs font-bold text-muted-foreground"
        >
          ترتیب
        </label>
        <select
          id="mobile-ordering"
          name="ordering"
          defaultValue={query.ordering}
          className="min-h-11 min-w-0 flex-1 rounded-full border border-gold/45 bg-background px-3 text-sm font-semibold text-foreground"
        >
          {ORDERING_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="min-h-11 shrink-0 rounded-full bg-primary px-4 text-xs font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          اعمال
        </button>
      </form>

      <nav aria-label="مرتب‌سازی محصولات" className="hidden lg:block">
        <ul className="flex items-center gap-1">
          <li className="px-2 text-xs font-bold text-muted-foreground">ترتیب:</li>
          {ORDERING_OPTIONS.map((option) => {
            const isActive = option.value === query.ordering;

            return (
              <li key={option.value}>
                <Link
                  href={catalogHref(query, {
                    ordering: option.value,
                    page: 1,
                  })}
                  aria-current={isActive ? "page" : undefined}
                  className={`inline-flex min-h-10 items-center rounded-full px-3 text-xs font-bold transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-background hover:text-primary"
                  }`}
                >
                  {option.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
