import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import {
  CatalogDiscovery,
  CatalogSidebar,
  CatalogToolbar,
} from "@/components/catalog-controls";
import { Container } from "@/components/container";
import { Pagination } from "@/components/pagination";
import { ProductCard } from "@/components/product-card";
import {
  CatalogApiError,
  type Category,
  getCategories,
  getProducts,
  type ProductPage,
  PRODUCTS_PAGE_SIZE,
} from "@/lib/catalog-api";
import {
  catalogHref,
  catalogQueryNeedsNormalization,
  DEFAULT_PRODUCT_ORDERING,
  parseCatalogQuery,
  type RawCatalogSearchParams,
} from "@/lib/catalog-query";

export const metadata: Metadata = {
  title: "محصولات | نقش‌جهان",
  description: "مرور محصولات و دسته‌بندی‌های فعال فروشگاه نقش‌جهان",
};

type ProductsPageProps = {
  searchParams: Promise<RawCatalogSearchParams>;
};

function EmptyCatalog({ filtered }: { filtered: boolean }) {
  return (
    <section className="rounded-[1.5rem] border border-gold/35 bg-surface px-5 py-14 text-center shadow-card sm:px-8 sm:py-20">
      <div
        className="mx-auto flex size-16 items-center justify-center rounded-full border-2 border-gold bg-background text-primary"
        aria-hidden="true"
      >
        <svg viewBox="0 0 48 48" fill="none" className="size-7">
          <path
            d="M8 15.5 24 7l16 8.5v17L24 41 8 32.5v-17Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <path
            d="m8.5 15.5 15.5 9 15.5-9M24 24.5V41"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h2 className="mt-6 text-xl font-extrabold text-foreground sm:text-2xl">
        {filtered ? "نتیجه‌ای پیدا نشد" : "هنوز محصولی برای نمایش نیست"}
      </h2>
      <p className="mx-auto mt-3 max-w-md leading-8 text-muted-foreground">
        {filtered
          ? "عبارت جست‌وجو یا انتخاب‌های فعلی را تغییر دهید و دوباره امتحان کنید."
          : "به‌محض اضافه‌شدن محصولات فعال، آن‌ها را در همین صفحه خواهید دید."}
      </p>
      {filtered ? (
        <Link
          href="/products"
          className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 text-sm font-bold text-primary-foreground shadow-card transition hover:bg-primary-hover"
        >
          نمایش همهٔ محصولات
        </Link>
      ) : null}
    </section>
  );
}

function CatalogError({
  missingPage,
  returnHref,
}: {
  missingPage: boolean;
  returnHref: string;
}) {
  return (
    <section
      role="alert"
      className="rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-5 py-12 text-center sm:px-8 sm:py-16"
    >
      <div
        aria-hidden="true"
        className="mx-auto flex size-14 items-center justify-center rounded-full border border-destructive/25 bg-surface text-2xl font-black text-destructive"
      >
        !
      </div>
      <h2 className="mt-5 text-xl font-extrabold text-foreground sm:text-2xl">
        {missingPage
          ? "این صفحه از محصولات وجود ندارد"
          : "دریافت محصولات ممکن نشد"}
      </h2>
      <p className="mx-auto mt-3 max-w-lg leading-8 text-muted-foreground">
        {missingPage
          ? "شمارهٔ صفحه معتبر نیست یا از محدودهٔ فهرست خارج شده است."
          : "ارتباط با سرویس فروشگاه برقرار نشد. لطفاً کمی بعد دوباره تلاش کنید."}
      </p>
      <Link
        href={returnHref}
        className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
      >
        {missingPage ? "بازگشت به صفحهٔ اول نتایج" : "تلاش دوباره"}
      </Link>
    </section>
  );
}

function CatalogHeading({ query, categories }: { query: ReturnType<typeof parseCatalogQuery>; categories: Category[] }) {
  const category = categories.find((item) => item.slug === query.category);
  const title = category?.name
    ? category.name
    : query.search
      ? `نتایج جست‌وجوی «${query.search}»`
      : "گنجینهٔ نقش‌جهان";

  return (
    <header className="naghsh-pattern relative isolate overflow-hidden rounded-[1.5rem] px-5 py-11 text-center text-white sm:px-10 sm:py-14 lg:py-16">
      <div className="absolute inset-0 -z-10 bg-lapis-dark/82" />
      <p className="flex items-center justify-center gap-3 text-xs font-black text-gold-light sm:text-sm">
        <span className="size-2 rotate-45 bg-gold" aria-hidden="true" />
        محصولات فروشگاه
        <span className="size-2 rotate-45 bg-gold" aria-hidden="true" />
      </p>
      <h1 className="mx-auto mt-4 max-w-3xl text-3xl font-black leading-[1.45] tracking-tight text-white sm:text-4xl">
        {title}
      </h1>
      <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-white/72 sm:text-base sm:leading-8">
        محصولات فعال را با تصویر، قیمت و موجودی ثبت‌شده در کاتالوگ مرور کنید.
      </p>
    </header>
  );
}

export default async function ProductsPage({ searchParams }: ProductsPageProps) {
  const rawSearchParams = await searchParams;
  const query = parseCatalogQuery(rawSearchParams);

  if (catalogQueryNeedsNormalization(rawSearchParams, query)) {
    redirect(catalogHref(query));
  }

  const currentPage = query.page;
  let products: ProductPage | null = null;
  let categories: Category[] = [];
  let requestError: unknown;
  let categoriesUnavailable = false;

  const [productsResult, categoriesResult] = await Promise.allSettled([
    getProducts(query),
    getCategories(),
  ]);

  if (productsResult.status === "fulfilled") {
    products = productsResult.value;
  } else {
    requestError = productsResult.reason;
  }

  if (categoriesResult.status === "fulfilled") {
    categories = categoriesResult.value;
  } else {
    categoriesUnavailable = true;
  }

  if (!products) {
    return (
      <Container className="py-6 sm:py-9 lg:py-12">
        <CatalogHeading query={query} categories={categories} />
        <div className="mt-8 sm:mt-10">
          <CatalogError
            missingPage={
              requestError instanceof CatalogApiError && requestError.status === 404
            }
            returnHref={catalogHref(query, { page: 1 })}
          />
        </div>
      </Container>
    );
  }

  const totalPages = Math.max(
    1,
    Math.ceil(products.count / PRODUCTS_PAGE_SIZE),
  );

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <CatalogHeading query={query} categories={categories} />
      <CatalogDiscovery categories={categories} query={query} />

      <div className="mt-8 grid min-w-0 gap-7 lg:grid-cols-[17rem_minmax(0,1fr)] lg:items-start xl:gap-9">
        <CatalogSidebar
          categories={categories}
          categoriesUnavailable={categoriesUnavailable}
          query={query}
        />

        <div className="min-w-0">
          <CatalogToolbar
            categories={categories}
            categoriesUnavailable={categoriesUnavailable}
            query={query}
            resultCount={products.count}
          />

          {products.results.length === 0 ? (
            <div className="mt-7 sm:mt-9">
              <EmptyCatalog
                filtered={Boolean(
                  query.search ||
                    query.category ||
                    query.ordering !== DEFAULT_PRODUCT_ORDERING,
                )}
              />
            </div>
          ) : (
            <>
              <section
                aria-label="فهرست محصولات"
                className="mt-7 grid min-w-0 grid-cols-1 gap-5 min-[480px]:grid-cols-2 sm:gap-6 xl:grid-cols-3"
              >
                {products.results.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </section>
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                query={query}
              />
            </>
          )}
        </div>
      </div>
    </Container>
  );
}
