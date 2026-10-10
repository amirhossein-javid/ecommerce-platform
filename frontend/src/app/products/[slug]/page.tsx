import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AddToCartButton } from "@/components/add-to-cart-button";
import { Container } from "@/components/container";
import { ProductGallery } from "@/components/product-gallery";
import { ProductReviews } from "@/components/product-reviews";
import {
  CatalogApiError,
  getProduct,
  type ProductDetail,
} from "@/lib/catalog-api";
import { formatToman } from "@/lib/format-price";
import { getCustomerSession } from "@/lib/auth-session";
import {
  fetchProductReviewAggregate,
  fetchPublicProductReviews,
} from "@/lib/review-api";
import type {
  ProductReviewAggregate,
  PublicProductReview,
} from "@/lib/review-contract";

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
      title: `${product.name} | نقش‌جهان`,
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
          ? "محصول پیدا نشد | نقش‌جهان"
          : "محصول | نقش‌جهان",
    };
  }
}

function ProductDetailError() {
  return (
    <Container className="py-8 sm:py-12 lg:py-16">
      <section
        role="alert"
        className="mx-auto max-w-2xl rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-6 py-14 text-center sm:px-10"
      >
        <div
          className="mx-auto grid size-14 place-items-center rounded-full border border-destructive/25 bg-surface text-2xl font-black text-destructive"
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
          className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-hover"
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
  let reviews: PublicProductReview[] = [];
  let aggregate: ProductReviewAggregate = {
    average_rating: null,
    review_count: 0,
  };
  let publicError = false;
  const [reviewResult, session] = await Promise.all([
    Promise.all([
      fetchPublicProductReviews(product.slug),
      fetchProductReviewAggregate(product.slug),
    ]).catch(() => null),
    getCustomerSession(),
  ]);
  if (reviewResult) {
    reviews = reviewResult[0].results;
    aggregate = reviewResult[1];
  } else {
    publicError = true;
  }
  const accountState =
    session.state === "customer"
      ? "customer"
      : session.state === "guest"
        ? "guest"
        : "blocked";

  return (
    <Container className="py-5 sm:py-8 lg:py-11">
      <nav
        aria-label="مسیر صفحه"
        className="mb-5 min-w-0 text-xs text-muted-foreground sm:mb-7 sm:text-sm"
      >
        <ol className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <li>
            <Link
              href="/"
              className="rounded-full px-2 py-1 transition-colors hover:bg-primary-soft hover:text-primary"
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
              className="rounded-full px-2 py-1 transition-colors hover:bg-primary-soft hover:text-primary"
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

      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,0.82fr)_minmax(0,1.35fr)_minmax(16rem,0.83fr)] lg:items-start lg:gap-6 xl:grid-cols-[minmax(17rem,0.82fr)_minmax(27rem,1.35fr)_minmax(18rem,0.83fr)] xl:gap-8">
        <section
          aria-labelledby="product-title"
          className="min-w-0 lg:col-start-1 lg:row-start-1"
        >
          <Link
            href={`/products?category=${encodeURIComponent(product.category.slug)}`}
            className="inline-flex min-h-10 items-center rounded-full border border-primary/15 bg-primary-soft/70 px-4 text-sm font-bold text-primary transition-colors hover:bg-primary-soft"
          >
            {product.category.name}
          </Link>
          <h1
            id="product-title"
            className="mt-4 text-2xl font-black leading-[1.55] tracking-tight text-foreground sm:text-3xl lg:text-[1.8rem] xl:text-[2.15rem]"
          >
            {product.name}
          </h1>
        </section>

        <div className="min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <ProductGallery images={product.images} productName={product.name} />
        </div>

        <section
          aria-labelledby="product-information-title"
          className="min-w-0 rounded-[1.25rem] border border-gold/35 bg-surface p-5 shadow-card lg:col-start-1 lg:row-start-2"
        >
          <h2
            id="product-information-title"
            className="text-lg font-black text-foreground"
          >
            اطلاعات محصول
          </h2>

          <dl className="mt-4 divide-y divide-gold/25 border-y border-gold/30 text-sm">
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
          className="min-w-0 overflow-hidden rounded-[1.5rem] border border-gold/45 bg-surface p-5 shadow-card lg:sticky lg:top-28 lg:col-start-3 lg:row-span-2 lg:row-start-1 xl:p-6"
        >
          <p className="mb-2 flex items-center gap-2 text-xs font-black text-primary"><span className="size-1.5 rotate-45 bg-gold" aria-hidden="true" /> انتخاب شما</p>
          <h2
            id="purchase-summary-title"
            className="text-base font-black text-foreground"
          >
            خلاصهٔ خرید
          </h2>

          <div className="mt-5 rounded-[1.1rem] bg-background px-4 py-5">
            <p className="text-sm font-semibold text-muted-foreground">
              قیمت محصول
            </p>
            <p className="mt-2 break-words text-2xl font-black leading-10 tabular-nums text-lapis xl:text-[1.7rem]">
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
                  ? "این محصول برای افزودن به سبد خرید در دسترس است."
                  : "این محصول فعلاً قابل سفارش نیست."}
              </p>
            </div>
          </div>

          {product.in_stock ? (
            <div className="mt-6 border-t border-gold/30 pt-6">
              <AddToCartButton
                productPrice={product.price}
                productSlug={product.slug}
              />
            </div>
          ) : null}
        </aside>
      </div>
      <ProductReviews
        key={`${product.slug}:${aggregate.review_count}:${aggregate.average_rating ?? "empty"}:${reviews.map((review) => review.id).join(",")}`}
        productSlug={product.slug}
        reviews={reviews}
        aggregate={aggregate}
        publicError={publicError}
        accountState={accountState}
      />
    </Container>
  );
}
