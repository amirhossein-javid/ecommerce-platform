import type { Metadata } from "next";

import { Container } from "@/components/container";
import { Pagination } from "@/components/pagination";
import { ProductCard } from "@/components/product-card";
import {
  CatalogApiError,
  getProducts,
  type ProductPage,
  PRODUCTS_PAGE_SIZE,
} from "@/lib/catalog-api";

export const metadata: Metadata = {
  title: "محصولات | فروشگاه",
  description: "فهرست محصولات فروشگاه",
};

type ProductsPageProps = {
  searchParams: Promise<{ page?: string | string[] }>;
};

function parsePage(value: string | string[] | undefined) {
  const candidate = Array.isArray(value) ? value[0] : value;

  if (!candidate || !/^\d+$/.test(candidate)) {
    return 1;
  }

  const page = Number(candidate);
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}

function EmptyCatalog() {
  return (
    <section className="rounded-2xl border border-dashed border-border bg-surface px-5 py-14 text-center shadow-card sm:px-8 sm:py-20">
      <div
        className="mx-auto flex size-16 items-center justify-center rounded-xl border border-border bg-surface-muted text-primary"
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
        هنوز محصولی برای نمایش نیست
      </h2>
      <p className="mx-auto mt-3 max-w-md leading-8 text-muted-foreground">
        به‌محض اضافه‌شدن محصولات فعال، آن‌ها را در همین صفحه خواهید دید.
      </p>
    </section>
  );
}

function CatalogError({ missingPage }: { missingPage: boolean }) {
  return (
    <section
      role="alert"
      className="rounded-2xl border border-destructive/25 bg-destructive-soft/45 px-5 py-12 text-center shadow-card sm:px-8 sm:py-16"
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
      <a
        href="/products"
        className="mt-7 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
      >
        بازگشت به ابتدای فهرست
      </a>
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
  const { page: pageParam } = await searchParams;
  const currentPage = parsePage(pageParam);
  let products: ProductPage | null = null;
  let requestError: unknown;

  try {
    products = await getProducts(currentPage);
  } catch (error) {
    requestError = error;
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

      {products.results.length === 0 ? (
        <div className="mt-8 sm:mt-10">
          <EmptyCatalog />
        </div>
      ) : (
        <>
          <section
            aria-label="فهرست محصولات"
            className="mt-8 grid min-w-0 grid-cols-1 gap-x-6 gap-y-8 sm:mt-10 sm:grid-cols-2 lg:grid-cols-3 lg:gap-x-7 lg:gap-y-10"
          >
            {products.results.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </section>
          <Pagination currentPage={currentPage} totalPages={totalPages} />
        </>
      )}
    </Container>
  );
}
