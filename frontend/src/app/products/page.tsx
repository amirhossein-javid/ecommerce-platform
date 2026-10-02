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
    <section className="rounded-lg border border-dashed border-border bg-surface px-5 py-14 text-center sm:px-8 sm:py-20">
      <div
        className="mx-auto flex size-14 items-center justify-center rounded-full bg-surface-subtle text-muted-foreground"
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
      <h2 className="mt-5 text-xl font-bold text-foreground">
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
      className="rounded-lg border border-destructive/25 bg-surface px-5 py-12 text-center sm:px-8 sm:py-16"
    >
      <h2 className="text-xl font-bold text-foreground">
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
        className="mt-6 inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-5 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary/90"
      >
        بازگشت به ابتدای فهرست
      </a>
    </section>
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
      <Container className="py-8 sm:py-12 lg:py-16">
        <header className="mb-8 border-b border-border pb-7 sm:mb-10">
          <p className="text-sm font-semibold text-primary">فروشگاه</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">
            محصولات
          </h1>
        </header>
        <CatalogError
          missingPage={
            requestError instanceof CatalogApiError && requestError.status === 404
          }
        />
      </Container>
    );
  }

  const totalPages = Math.max(
    1,
    Math.ceil(products.count / PRODUCTS_PAGE_SIZE),
  );

  return (
    <Container className="py-8 sm:py-12 lg:py-16">
      <header className="mb-8 flex flex-col gap-3 border-b border-border pb-7 sm:mb-10 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-primary">فروشگاه</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">
            محصولات
          </h1>
        </div>
        <p className="text-sm font-medium text-muted-foreground">
          {products.count.toLocaleString("fa-IR")} محصول
        </p>
      </header>

      {products.results.length === 0 ? (
        <EmptyCatalog />
      ) : (
        <>
          <section
            aria-label="فهرست محصولات"
            className="grid min-w-0 grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
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
