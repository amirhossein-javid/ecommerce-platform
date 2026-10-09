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
  title: "محصولات | فروشگاه",
  description: "فهرست محصولات فروشگاه",
};

type ProductsPageProps = {
  searchParams: Promise<RawCatalogSearchParams>;
};

function EmptyCatalog({ filtered }: { filtered: boolean }) {
  return (
    <section className="rounded-xl bg-surface-muted/55 px-5 py-14 text-center sm:px-8 sm:py-20">
      <div
        className="mx-auto flex size-16 items-center justify-center rounded-xl bg-primary-soft/70 text-primary"
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
          className="mt-7 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
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
      className="rounded-xl bg-destructive-soft/45 px-5 py-12 text-center sm:px-8 sm:py-16"
    >
      <div
        aria-hidden="true"
        className="mx-auto flex size-14 items-center justify-center rounded-xl bg-destructive-soft text-2xl font-black text-destructive"
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
        className="mt-7 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
      >
        {missingPage ? "بازگشت به صفحهٔ اول نتایج" : "تلاش دوباره"}
      </Link>
    </section>
  );
}

function CatalogHeading() {
  return (
    <header className="border-b border-border pb-6 sm:pb-8">
      <div className="max-w-2xl">
        <p className="flex items-center gap-3 text-sm font-bold text-primary">
          <span className="h-px w-8 bg-primary" aria-hidden="true" />
          کاتالوگ فروشگاه
        </p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-foreground sm:text-4xl">
          محصولات
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-7 text-muted-foreground sm:text-base sm:leading-8">
          محصولات فعال فروشگاه را با قیمت و وضعیت موجودی به‌روز مرور کنید.
        </p>
      </div>
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
      <Container className="py-7 sm:py-10 lg:py-14">
        <CatalogHeading />
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
    <Container className="py-7 sm:py-10 lg:py-14">
      <CatalogHeading />
      <CatalogDiscovery categories={categories} query={query} />

      <div className="mt-7 grid min-w-0 gap-7 lg:grid-cols-[17rem_minmax(0,1fr)] lg:items-start xl:gap-8">
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
                className="mt-7 grid min-w-0 grid-cols-1 gap-x-3 gap-y-8 min-[360px]:grid-cols-2 sm:gap-x-5 sm:gap-y-10 xl:grid-cols-3 xl:gap-x-6"
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
