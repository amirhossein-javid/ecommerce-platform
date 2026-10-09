import Link from "next/link";

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

const fieldClasses =
  "min-h-12 w-full min-w-0 rounded-lg border border-border bg-surface px-3 text-sm font-semibold text-foreground shadow-[0_1px_0_rgb(var(--shadow-color)/0.03)] transition-colors hover:border-primary/35";

function FilterFields({
  categories,
  categoriesUnavailable,
  query,
  idPrefix,
}: Omit<CatalogControlsProps, "resultCount"> & { idPrefix: string }) {
  return (
    <>
      {query.search ? <input type="hidden" name="search" value={query.search} /> : null}
      {categoriesUnavailable && query.category ? (
        <input type="hidden" name="category" value={query.category} />
      ) : null}
      <div className="min-w-0">
        <label
          htmlFor={`${idPrefix}-category`}
          className="mb-1.5 block text-xs font-bold text-muted-foreground"
        >
          دسته‌بندی
        </label>
        <select
          id={`${idPrefix}-category`}
          name="category"
          defaultValue={query.category}
          disabled={categoriesUnavailable}
          className={fieldClasses}
        >
          {categoriesUnavailable ? (
            <option value={query.category}>
              دسته‌بندی‌ها موقتاً در دسترس نیستند
            </option>
          ) : (
            <>
              <option value="">همهٔ دسته‌بندی‌ها</option>
              {categories.map((category) => (
                <option key={category.id} value={category.slug}>
                  {category.parent
                    ? `${category.parent.name} — ${category.name}`
                    : category.name}
                </option>
              ))}
            </>
          )}
        </select>
      </div>

      <div className="min-w-0">
        <label
          htmlFor={`${idPrefix}-ordering`}
          className="mb-1.5 block text-xs font-bold text-muted-foreground"
        >
          مرتب‌سازی
        </label>
        <select
          id={`${idPrefix}-ordering`}
          name="ordering"
          defaultValue={query.ordering}
          className={fieldClasses}
        >
          {ORDERING_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        className="min-h-12 self-end rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
      >
        اعمال
      </button>
    </>
  );
}

export function CatalogControls({
  categories,
  categoriesUnavailable,
  query,
  resultCount,
}: CatalogControlsProps) {
  const selectedCategory = categories.find(
    (category) => category.slug === query.category,
  );
  const selectedOrdering = ORDERING_OPTIONS.find(
    (option) => option.value === query.ordering,
  );
  const activeFilterCount =
    Number(Boolean(query.category)) +
    Number(query.ordering !== DEFAULT_PRODUCT_ORDERING);
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
    <section aria-labelledby="catalog-discovery-title" className="mt-7 sm:mt-9">
      <h2 id="catalog-discovery-title" className="sr-only">
        جست‌وجو و پالایش محصولات
      </h2>

      <div className="rounded-2xl border border-border bg-surface p-4 shadow-card sm:p-5 lg:p-6">
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
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row">
            <div className="relative min-w-0 flex-1">
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 start-4 grid place-items-center text-muted-foreground"
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
                placeholder="جست‌وجو در نام و توضیحات محصولات"
                enterKeyHint="search"
                className={`${fieldClasses} ps-12 sm:text-base`}
              />
            </div>
            <button
              type="submit"
              className="min-h-12 shrink-0 rounded-lg bg-primary px-6 text-sm font-bold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
            >
              جست‌وجو
            </button>
          </div>
        </form>

        <form
          action="/products"
          method="get"
          aria-label="فیلتر و مرتب‌سازی محصولات"
          className="mt-5 hidden grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-4 border-t border-border pt-5 sm:grid"
        >
          <FilterFields
            categories={categories}
            categoriesUnavailable={categoriesUnavailable}
            query={query}
            idPrefix="desktop"
          />
        </form>

        <details className="mt-4 border-t border-border pt-4 sm:hidden">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 rounded-lg px-1 text-sm font-extrabold text-foreground">
            <span>فیلتر و مرتب‌سازی</span>
            {activeFilterCount > 0 ? (
              <span className="grid min-w-7 place-items-center rounded-full bg-primary-soft px-2 py-0.5 text-xs text-primary">
                {activeFilterCount.toLocaleString("fa-IR")}
              </span>
            ) : null}
          </summary>
          <form
            action="/products"
            method="get"
            aria-label="فیلتر و مرتب‌سازی محصولات در موبایل"
            className="mt-3 grid gap-4 rounded-xl bg-surface-muted/55 p-4"
          >
            <FilterFields
              categories={categories}
              categoriesUnavailable={categoriesUnavailable}
              query={query}
              idPrefix="mobile"
            />
          </form>
        </details>
      </div>

      <div className="mt-6 flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground" aria-live="polite">
          <strong className="text-base font-black text-foreground">
            {resultCount.toLocaleString("fa-IR")}
          </strong>{" "}
          محصول پیدا شد
        </p>

        {hasDiscoveryState ? (
          <Link
            href="/products"
            className="inline-flex min-h-11 w-fit items-center rounded-lg px-2 text-sm font-bold text-primary transition-colors hover:bg-primary-soft/65"
          >
            پاک‌کردن همهٔ انتخاب‌ها
          </Link>
        ) : null}
      </div>

      {activeItems.length > 0 ? (
        <ul aria-label="انتخاب‌های فعال" className="mt-3 flex min-w-0 flex-wrap gap-2">
          {activeItems.map((item) => (
            <li key={item.key} className="min-w-0 max-w-full">
              <Link
                href={item.href}
                aria-label={`حذف ${item.label}`}
                className="inline-flex min-h-11 max-w-full items-center gap-2 rounded-full border border-primary/15 bg-primary-soft/60 px-3 text-xs font-bold text-primary transition-colors hover:border-primary/30 hover:bg-primary-soft"
              >
                <span className="truncate">{item.label}</span>
                <span aria-hidden="true" className="text-base leading-none">
                  ×
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
