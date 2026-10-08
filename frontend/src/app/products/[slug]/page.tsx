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
        className="mx-auto max-w-2xl rounded-2xl border border-destructive/25 bg-destructive-soft/45 px-6 py-14 text-center shadow-card sm:px-10"
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
          className="mt-7 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
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

      <div className="grid min-w-0 gap-8 lg:grid-cols-[minmax(0,1.08fr)_minmax(20rem,0.92fr)] lg:items-start lg:gap-12 xl:gap-16">
        <ProductGallery images={product.images} productName={product.name} />

        <section
          aria-labelledby="product-title"
          className="min-w-0 lg:sticky lg:top-28"
        >
          <p className="text-sm font-bold text-primary">
            {product.category.name}
          </p>
          <h1
            id="product-title"
            className="mt-3 text-3xl font-black leading-[1.45] tracking-tight text-foreground sm:text-4xl lg:text-[2.65rem]"
          >
            {product.name}
          </h1>

          <div className="mt-7 flex items-center gap-3 border-y border-border py-4">
            <span
              aria-hidden="true"
              className={`size-2.5 rounded-full ${
                product.in_stock ? "bg-success" : "bg-destructive"
              }`}
            />
            <p
              className={`text-sm font-extrabold ${
                product.in_stock ? "text-success" : "text-destructive"
              }`}
            >
              {product.in_stock ? "موجود در فروشگاه" : "در حال حاضر ناموجود"}
            </p>
          </div>

          <div className="mt-7 rounded-2xl border border-primary/10 bg-primary-soft/65 px-5 py-5 sm:px-6">
            <p className="text-sm font-semibold text-muted-foreground">قیمت</p>
            <p className="mt-2 break-words text-2xl font-black leading-10 tabular-nums text-primary sm:text-3xl">
              <bdi>{formatToman(product.price)}</bdi>
            </p>
          </div>

          {!product.in_stock ? (
            <p className="mt-5 rounded-xl border border-destructive/20 bg-destructive-soft/45 px-4 py-3 text-sm font-semibold leading-7 text-destructive">
              این محصول فعلاً قابل سفارش نیست.
            </p>
          ) : null}
        </section>
      </div>

      <section
        aria-labelledby="product-description"
        className="mt-12 border-t border-border pt-9 sm:mt-16 sm:pt-11 lg:mt-20 lg:max-w-4xl"
      >
        <p className="text-sm font-bold text-primary">دربارهٔ محصول</p>
        <h2
          id="product-description"
          className="mt-2 text-2xl font-black tracking-tight text-foreground sm:text-3xl"
        >
          معرفی و توضیحات
        </h2>
        {description ? (
          <p className="mt-5 whitespace-pre-line text-base leading-9 text-muted-foreground sm:text-lg sm:leading-10">
            {description}
          </p>
        ) : (
          <p className="mt-5 text-base leading-8 text-muted-foreground">
            توضیحی برای این محصول ثبت نشده است.
          </p>
        )}
      </section>
    </Container>
  );
}
