import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Container } from "@/components/container";
import { ProductGallery } from "@/components/product-gallery";
import {
  CatalogApiError,
  getProduct,
  type ProductDetail,
} from "@/lib/catalog-api";
import { formatToman } from "@/lib/format-price";

type ProductDetailPageProps = {
  params: Promise<{ slug: string }>;
};

function getMetadataDescription(product: ProductDetail) {
  const description = product.description.replace(/\s+/g, " ").trim();

  if (!description) {
    return `مشاهدهٔ مشخصات، قیمت و تصاویر ${product.name}`;
  }

  return description.length > 155
    ? `${description.slice(0, 152).trimEnd()}…`
    : description;
}

export async function generateMetadata({
  params,
}: ProductDetailPageProps): Promise<Metadata> {
  const { slug } = await params;

  try {
    const product = await getProduct(slug);
    const description = getMetadataDescription(product);
    const primaryImage =
      product.images.find((image) => image.is_primary) ?? product.images[0];

    return {
      title: `${product.name} | فروشگاه`,
      description,
      openGraph: {
        title: product.name,
        description,
        locale: "fa_IR",
        type: "website",
        images: primaryImage
          ? [
              {
                url: primaryImage.image,
                alt: primaryImage.alt_text || product.name,
              },
            ]
          : undefined,
      },
    };
  } catch (error) {
    return {
      title:
        error instanceof CatalogApiError && error.status === 404
          ? "محصول پیدا نشد | فروشگاه"
          : "محصول | فروشگاه",
    };
  }
}

function ProductDetailError() {
  return (
    <Container className="py-10 sm:py-14 lg:py-20">
      <section
        role="alert"
        className="mx-auto max-w-2xl rounded-xl bg-destructive-soft/45 px-6 py-14 text-center sm:px-10"
      >
        <div
          className="mx-auto grid size-14 place-items-center rounded-xl bg-destructive-soft text-2xl font-black text-destructive"
          aria-hidden="true"
        >
          !
        </div>
        <h1 className="mt-5 text-2xl font-black text-foreground">
          دریافت اطلاعات محصول ممکن نشد
        </h1>
        <p className="mx-auto mt-3 max-w-lg leading-8 text-muted-foreground">
          ارتباط با سرویس فروشگاه برقرار نشد. لطفاً کمی بعد دوباره تلاش کنید.
        </p>
        <Link
          href="/products"
          className="mt-7 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          بازگشت به محصولات
        </Link>
      </section>
    </Container>
  );
}

export default async function ProductDetailPage({
  params,
}: ProductDetailPageProps) {
  const { slug } = await params;
  let product: ProductDetail;

  try {
    product = await getProduct(slug);
  } catch (error) {
    if (error instanceof CatalogApiError && error.status === 404) {
      notFound();
    }

    return <ProductDetailError />;
  }

  const description = product.description.trim();

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <nav
        aria-label="مسیر صفحه"
        className="mb-6 min-w-0 text-sm text-muted-foreground sm:mb-8"
      >
        <ol className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <li>
            <Link
              href="/"
              className="rounded-sm transition-colors hover:text-primary"
            >
              خانه
            </Link>
          </li>
          <li aria-hidden="true" className="text-border">
            /
          </li>
          <li>
            <Link
              href="/products"
              className="rounded-sm transition-colors hover:text-primary"
            >
              محصولات
            </Link>
          </li>
          <li aria-hidden="true" className="text-border">
            /
          </li>
          <li
            className="min-w-0 truncate font-semibold text-foreground"
            aria-current="page"
          >
            {product.name}
          </li>
        </ol>
      </nav>

      <div className="grid min-w-0 gap-8 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.32fr)_minmax(15rem,0.8fr)] lg:items-start lg:gap-6 xl:grid-cols-[minmax(17rem,0.88fr)_minmax(26rem,1.35fr)_minmax(17rem,0.77fr)] xl:gap-8">
        <section
          aria-labelledby="product-title"
          className="min-w-0 lg:col-start-1 lg:row-start-1"
        >
          <Link
            href={`/products?category=${encodeURIComponent(product.category.slug)}`}
            className="inline-flex min-h-10 items-center rounded-lg bg-primary-soft/65 px-3 text-sm font-bold text-primary transition-colors hover:bg-primary-soft"
          >
            {product.category.name}
          </Link>
          <h1
            id="product-title"
            className="mt-4 text-2xl font-black leading-[1.55] tracking-tight text-foreground sm:text-3xl lg:text-[1.75rem] xl:text-[2rem]"
          >
            {product.name}
          </h1>
        </section>

        <div className="min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <ProductGallery images={product.images} productName={product.name} />
        </div>

        <section
          aria-labelledby="product-information-title"
          className="min-w-0 border-t border-border/75 pt-6 lg:col-start-1 lg:row-start-2"
        >
          <h2
            id="product-information-title"
            className="text-lg font-black text-foreground"
          >
            اطلاعات محصول
          </h2>

          <dl className="mt-4 divide-y divide-border/70 border-y border-border/70 text-sm">
            <div className="flex items-center justify-between gap-4 py-3.5">
              <dt className="text-muted-foreground">دسته‌بندی</dt>
              <dd className="font-extrabold text-foreground">
                {product.category.name}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-3.5">
              <dt className="text-muted-foreground">وضعیت</dt>
              <dd
                className={`font-extrabold ${
                  product.in_stock ? "text-success" : "text-destructive"
                }`}
              >
                {product.in_stock ? "موجود" : "ناموجود"}
              </dd>
            </div>
          </dl>

          <div className="mt-7">
            <h2 className="text-lg font-black text-foreground">معرفی محصول</h2>
            {description ? (
              <p className="mt-3 whitespace-pre-line text-sm leading-8 text-muted-foreground sm:text-base sm:leading-9">
                {description}
              </p>
            ) : (
              <p className="mt-3 text-sm leading-8 text-muted-foreground">
                توضیحی برای این محصول ثبت نشده است.
              </p>
            )}
          </div>
        </section>

        <aside
          aria-labelledby="purchase-summary-title"
          className="min-w-0 rounded-xl border border-border/80 bg-surface p-5 lg:sticky lg:top-28 lg:col-start-3 lg:row-span-2 lg:row-start-1 xl:p-6"
        >
          <h2
            id="purchase-summary-title"
            className="text-base font-black text-foreground"
          >
            خلاصهٔ خرید
          </h2>

          <div className="mt-5 border-y border-border/70 py-5">
            <p className="text-sm font-semibold text-muted-foreground">
              قیمت محصول
            </p>
            <p className="mt-2 break-words text-2xl font-black leading-10 tabular-nums text-primary xl:text-[1.7rem]">
              <bdi>{formatToman(product.price)}</bdi>
            </p>
          </div>

          <div className="mt-5 flex items-start gap-3">
            <span
              aria-hidden="true"
              className={`mt-2 size-2 shrink-0 rounded-full ${
                product.in_stock ? "bg-success" : "bg-destructive"
              }`}
            />
            <div>
              <p
                className={`text-sm font-extrabold ${
                  product.in_stock ? "text-success" : "text-destructive"
                }`}
              >
                {product.in_stock
                  ? "موجود در فروشگاه"
                  : "در حال حاضر ناموجود"}
              </p>
              <p className="mt-1 text-xs leading-6 text-muted-foreground">
                {product.in_stock
                  ? "امکان سفارش پس از فعال‌شدن سبد خرید فراهم می‌شود."
                  : "این محصول فعلاً قابل سفارش نیست."}
              </p>
            </div>
          </div>
        </aside>
      </div>
    </Container>
  );
}
